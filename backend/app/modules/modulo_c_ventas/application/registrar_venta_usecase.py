# Caso de uso: registrar una venta en el POS, descontando stock de forma atómica.
# El escaneo ocurre en el frontend (el lector emula un teclado); aquí llegan los
# producto_id ya resueltos. Nombre y precio se guardan como snapshot (RF-18).
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import DetalleVenta, Venta
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.producto_stock_port import ProductoStockPort
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import monto_dinero
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError, ValidacionError

METODOS_VALIDOS = {"EFECTIVO", "YAPE", "PLIN", "TARJETA", "TRANSFERENCIA"}


class RegistrarVentaUseCase:
    def __init__(
        self,
        venta_repo: VentaRepositoryPort,
        caja_repo: CajaRepositoryPort,
        stock: ProductoStockPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._ventas = venta_repo
        self._caja = caja_repo
        self._stock = stock
        self._auditoria = auditoria

    async def ejecutar(
        self,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        items: list[tuple[int, int]],  # (producto_id, cantidad)
        metodo_pago: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Venta:
        # HU-C06: sin turno abierto no se puede vender.
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("No hay un turno de caja abierto. Abre la caja para poder vender.")

        metodo = metodo_pago.strip().upper()
        if metodo not in METODOS_VALIDOS:
            raise ValidacionError(f"Método de pago no válido: {metodo_pago}.")

        if not items:
            raise ValidacionError("La venta no tiene productos.")

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

        total = monto_dinero(sum(d.subtotal for d in detalles))
        venta = await self._ventas.crear(
            Venta(
                id=None,
                turno_id=turno.id,
                usuario_id=usuario_id,
                vendedor=nombre_usuario,
                total=total,
                metodo_pago=metodo,
                detalles=detalles,
            )
        )
        await self._auditoria.ejecutar(
            accion="venta_registrada", entidad="ventas", entidad_id=venta.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={
                "total": float(total),
                "metodo_pago": metodo,
                "turno_id": turno.id,
                "items": [{"producto_id": d.producto_id, "cantidad": d.cantidad} for d in detalles],
            },
            ip=ip, user_agent=user_agent,
        )
        return venta
