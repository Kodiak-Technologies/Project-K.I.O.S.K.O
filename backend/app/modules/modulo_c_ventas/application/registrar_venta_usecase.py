# Caso de uso: registrar una venta en el POS, descontando stock de forma atómica.
# El escaneo ocurre en el frontend (el lector emula un teclado); aquí llegan los
# producto_id ya resueltos. Nombre y precio se guardan como snapshot (RF-18).
#
# Pagos (RF-20): ninguna venta se confirma sin método de pago; admite pago mixto
# (parte efectivo, parte digital) y calcula el vuelto del efectivo. La suma de
# los pagos debe cuadrar exactamente con el total (RNF-03).
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import DetalleVenta, PagoVenta, Venta
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.metodo_pago_repository_port import (
    MetodoPagoRepositoryPort,
)
from app.modules.modulo_c_ventas.domain.ports.producto_stock_port import ProductoStockPort
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import monto_dinero
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError, ProhibidoError, ValidacionError


class RegistrarVentaUseCase:
    def __init__(
        self,
        venta_repo: VentaRepositoryPort,
        caja_repo: CajaRepositoryPort,
        stock: ProductoStockPort,
        metodos_repo: MetodoPagoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._ventas = venta_repo
        self._caja = caja_repo
        self._stock = stock
        self._metodos = metodos_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        items: list[tuple[int, int]],  # (producto_id, cantidad)
        pagos: list[dict],  # [{metodo, monto|None, monto_recibido|None}]
        client_uuid: str | None = None,  # idempotencia de la sincronización offline
        registrada_offline: bool = False,
        vendida_en=None,  # momento real de la venta (modo offline)
        ip: str = "",
        user_agent: str = "",
    ) -> Venta:
        # RF-26: si esta venta ya se sincronizó antes (reintento del POS offline),
        # se devuelve la existente en vez de duplicarla.
        if client_uuid:
            existente = await self._ventas.buscar_por_uuid(client_uuid)
            if existente is not None:
                return existente

        # HU-C06: sin turno abierto no se puede vender.
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("No hay un turno de caja abierto. Abre la caja para poder vender.")

        if turno.asignado_a_id and turno.asignado_a_id != usuario_id and rol != "ADMIN":
            raise ProhibidoError("Este turno ha sido asignado a otro cajero.")

        if not items:
            raise ValidacionError("La venta no tiene productos.")
        if not pagos:
            raise ValidacionError("La venta no tiene método de pago (RF-20).")

        detalles = await self._armar_detalles_y_descontar_stock(items)
        total = monto_dinero(sum(d.subtotal for d in detalles))

        pagos_venta = await self._validar_pagos(pagos, total)
        resumen_metodo = pagos_venta[0].codigo_metodo if len(pagos_venta) == 1 else "MIXTO"

        venta = await self._ventas.crear(
            Venta(
                id=None,
                turno_id=turno.id,
                usuario_id=usuario_id,
                vendedor=nombre_usuario,
                total=total,
                metodo_pago=resumen_metodo,
                detalles=detalles,
                pagos=pagos_venta,
                client_uuid=client_uuid,
                registrada_offline=registrada_offline,
                vendida_en=vendida_en,
            )
        )

        await self._auditoria.ejecutar(
            accion="venta_registrada",
            entidad="ventas", entidad_id=venta.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={
                "total": float(total),
                "metodo_pago": resumen_metodo,
                "pagos": [{"metodo": p.codigo_metodo, "monto": float(p.monto)} for p in pagos_venta],
                "turno_id": turno.id,
                "items": [{"producto_id": d.producto_id, "cantidad": d.cantidad} for d in detalles],
            },
            ip=ip, user_agent=user_agent,
        )
        return venta

    async def _armar_detalles_y_descontar_stock(
        self, items: list[tuple[int, int]]
    ) -> list[DetalleVenta]:
        # Consolidar repetidos: escanear 2 veces el mismo producto = cantidad 2.
        cantidades: dict[int, int] = {}
        for producto_id, cantidad in items:
            if cantidad <= 0:
                raise ValidacionError("Las cantidades deben ser mayores a 0.")
            cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad

        productos = await self._stock.obtener_para_venta(list(cantidades))

        detalles: list[DetalleVenta] = []
        for producto_id, cantidad in cantidades.items():
            producto = productos.get(producto_id)
            if producto is None:
                raise NoEncontradoError(f"El producto {producto_id} no existe en el catálogo.")
            if not producto.activo:
                raise ValidacionError(f"'{producto.nombre}' está inactivo y no se puede vender.")
            # Descuento atómico: si otra venta ganó las últimas unidades, esto
            # devuelve False y toda la operación se revierte (RNF-03).
            if not await self._stock.descontar_stock(producto_id, cantidad):
                raise ConflictoError(
                    f"Stock insuficiente de '{producto.nombre}': quedan {producto.stock}."
                )
            detalles.append(
                DetalleVenta(
                    id=None,
                    producto_id=producto_id,
                    nombre=producto.nombre,
                    precio_unitario=producto.precio,
                    cantidad=cantidad,
                )
            )
        return detalles

    async def _validar_pagos(self, pagos: list[dict], total: Decimal) -> list[PagoVenta]:
        catalogo = {m.codigo: m for m in await self._metodos.listar(solo_activos=True)}

        pagos_venta: list[PagoVenta] = []
        for pago in pagos:
            codigo = str(pago.get("metodo", "")).strip().upper()
            metodo = catalogo.get(codigo)
            if metodo is None:
                raise ValidacionError(f"Método de pago no válido o inactivo: {codigo or '(vacío)'}.")
            # Si es un solo pago sin monto explícito, cubre el total.
            monto = monto_dinero(pago["monto"]) if pago.get("monto") is not None else total
            if monto <= 0:
                raise ValidacionError("Cada pago debe ser mayor a 0.")
            recibido = None
            if pago.get("monto_recibido") is not None:
                recibido = monto_dinero(pago["monto_recibido"])
                if not metodo.es_efectivo:
                    recibido = None  # el vuelto solo tiene sentido en efectivo
                elif recibido < monto:
                    raise ValidacionError(
                        f"El monto recibido en {codigo} (S/ {recibido}) no cubre S/ {monto}."
                    )
            pagos_venta.append(
                PagoVenta(
                    id=None,
                    codigo_metodo=codigo,
                    monto=monto,
                    es_efectivo=metodo.es_efectivo,
                    monto_recibido=recibido,
                    metodo_pago_id=metodo.id,
                )
            )

        suma = monto_dinero(sum(p.monto for p in pagos_venta))
        if suma != total:
            raise ValidacionError(
                f"Los pagos suman S/ {suma} pero la venta es S/ {total}: deben cuadrar exacto."
            )
        return pagos_venta
