# Caso de uso: aprobar una solicitud de ingreso (HU-B07, REQ-APR).
# - SELECT ... FOR UPDATE sobre la solicitud.
# - Por cada línea: UPDATE producto.stock atómico + APPEND movimiento 'ingreso'.
# - UPDATE solicitud a 'Aprobada' con revisado_por.
# - Si rowcount=0 en cualquier UPDATE de stock → ROLLBACK 409.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.ports.configuracion_repository_port import (
    ConfiguracionRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.entities import (
    DetalleSolicitud,
    MovimientoInventario,
    Producto,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.precios import (
    costo_unitario,
    precio_venta_sugerido,
)
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
    MovimientoInventarioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)


@dataclass
class AprobacionResultado:
    solicitud: SolicitudIngreso
    productos_actualizados: int
    unidades_agregadas: int
    monto_total: Decimal = Decimal("0")
    credito_registrado: bool = False
    #: Cuántos productos se dieron de alta en el catálogo al aprobar.
    productos_creados: int = 0


class AprobarIngresoUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        detalle_repo: DetalleSolicitudRepositoryPort,
        producto_repo: ProductoRepositoryPort,
        movimiento_repo: MovimientoInventarioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
        configuracion_repo: ConfiguracionRepositoryPort,
        compra_credito_usecase=None,
    ):
        self._solicitudes = solicitud_repo
        self._detalles = detalle_repo
        self._productos = producto_repo
        self._movimientos = movimiento_repo
        self._auditoria = auditoria
        # De acá sale el % de ganancia por defecto para los productos nuevos.
        self._configuracion = configuracion_repo
        # Opcional (los tests unitarios no lo inyectan): permite cargar la
        # compra a crédito del proveedor en la MISMA transacción (HU-B14).
        self._compra_credito = compra_credito_usecase

    async def _crear_producto_de_linea(
        self,
        d: DetalleSolicitud,
        margen_default: Decimal,
        usuario_id: int,
        usuario_nombre: str,
    ) -> DetalleSolicitud:
        """Da de alta el producto que propuso el cajero y ata la línea a él.

        El precio de venta sale del margen (el de la línea si la admin lo pisó,
        si no el del negocio) aplicado sobre el costo unitario derivado del
        total de la boleta. Nace con stock 0: el stock lo suma el movimiento de
        ingreso, igual que para cualquier otro producto.
        """
        codigo = (d.nuevo_codigo or "").strip()
        # El código pudo haberse dado de alta entre el registro y la aprobación.
        existente = await self._productos.buscar_por_codigo(codigo)
        if existente is not None and existente.deleted_at is None:
            raise ConflictoError(
                f"El código '{codigo}' ya pertenece a '{existente.nombre}'. "
                "Edita la solicitud para apuntar la línea a ese producto."
            )

        margen = d.margen_ganancia if d.margen_ganancia is not None else margen_default
        creado = await self._productos.crear(
            Producto(
                id=None,
                codigo=codigo,
                nombre=(d.nuevo_nombre or "").strip(),
                categoria_id=d.nuevo_categoria_id,
                precio=precio_venta_sugerido(d.precio_compra_total, d.cantidad, margen),
                precio_compra_actual=costo_unitario(d.precio_compra_total, d.cantidad),
                stock=0,
                creado_por=usuario_id,
                creado_por_nombre=usuario_nombre,
            )
        )
        await self._detalles.asignar_producto(d.id, creado.id)  # type: ignore[arg-type]
        d.producto_id = creado.id
        d.producto_nombre = creado.nombre
        d.producto_codigo = creado.codigo
        return d

    async def ejecutar(
        self,
        solicitud_id: int,
        usuario_id: int,
        usuario_nombre: str,
        registrar_credito: bool = False,
        ip: str = "",
        user_agent: str = "",
    ) -> AprobacionResultado:
        # 1) FOR UPDATE la solicitud
        solicitud = await self._solicitudes.find_by_id_for_update(solicitud_id)
        if solicitud is None:
            raise NoEncontradoError("La solicitud no existe.")
        if not solicitud.puede_ser_aprobada():
            raise ConflictoError("La solicitud ya fue revisada.")

        # 2) Por cada línea: incrementar stock atómico + APPEND movimiento
        detalles = await self._detalles.listar_por_solicitud(solicitud_id)
        productos_actualizados = 0
        productos_creados = 0
        unidades_agregadas = 0
        monto_total = Decimal("0")
        margen_default = (await self._configuracion.obtener()).margen_ganancia_default
        for d in detalles:
            # 2.a) Alta del producto propuesto por el cajero. Se hace ACÁ y no
            # al registrar la solicitud a propósito: crear productos exige
            # `productos.crear`, permiso que el cajero no tiene. Quien aprueba
            # sí, así que el catálogo sigue bajo control sin que el cajero
            # dependa de nadie para transcribir la boleta.
            if d.es_producto_nuevo:
                d = await self._crear_producto_de_linea(
                    d, margen_default, usuario_id, usuario_nombre
                )
                productos_creados += 1

            ok, _stock_actual = await self._productos.incrementar_stock_atomic(
                d.producto_id, d.cantidad
            )
            if not ok:
                # rowcount=0 → stock insuficiente, producto borrado, o error
                raise ConflictoError(
                    f"No se puede sumar {d.cantidad} al producto {d.producto_id}: "
                    "stock insuficiente o producto borrado."
                )
            await self._movimientos.append(
                MovimientoInventario.ingreso(
                    producto_id=d.producto_id,
                    cantidad=d.cantidad,
                    solicitud_ingreso_id=solicitud_id,
                    usuario_id=usuario_id,
                    usuario_nombre=usuario_nombre,
                )
            )
            # HU-B05/HU-B11: el precio de compra de la boleta pasa a ser el
            # precio de compra vigente del producto y queda en el historial
            # (antes se guardaba en el detalle y nunca llegaba al catálogo).
            # El unitario se deriva del total de línea; el total es el dato real.
            await self._productos.actualizar_precio(
                d.producto_id,
                None,
                costo_unitario(d.precio_compra_total, d.cantidad),
                usuario_id,
                usuario_nombre,
            )
            productos_actualizados += 1
            unidades_agregadas += d.cantidad
            # Se SUMAN los totales de línea. Reconstruirlos como cantidad ×
            # unitario redondeado descuadraría contra la boleta (20/7 → 20.02).
            monto_total += Decimal(str(d.precio_compra_total))

        # 3) Transición de estado
        solicitud.aprobar(usuario_id, usuario_nombre)
        await self._solicitudes.actualizar(solicitud)

        # 4) HU-B14 (opcional): cargar la compra a la deuda del proveedor en la
        #    misma transacción, dejando el vínculo con la solicitud.
        credito_registrado = False
        if registrar_credito and monto_total > 0:
            if solicitud.proveedor_id is None:
                raise ValidacionError(
                    "La solicitud no tiene proveedor: no se puede registrar la "
                    "compra a crédito."
                )
            if self._compra_credito is not None:
                from datetime import date as _date

                await self._compra_credito.ejecutar(
                    proveedor_id=solicitud.proveedor_id,
                    monto=monto_total,
                    fecha=_date.today(),
                    concepto=f"Ingreso de mercadería #{solicitud_id}",
                    solicitud_ingreso_id=solicitud_id,
                    usuario_id=usuario_id,
                    usuario_nombre=usuario_nombre,
                    ip=ip,
                    user_agent=user_agent,
                )
                credito_registrado = True

        await self._auditoria.ejecutar(
            accion="aprobar_ingreso",
            entidad="solicitudes_ingreso",
            usuario_id=usuario_id,
            rol="",
            entidad_id=solicitud_id,
            valor_nuevo={
                "unidades": unidades_agregadas,
                "productos": productos_actualizados,
                "productos_creados": productos_creados,
                "monto_total": float(monto_total),
                "credito_registrado": credito_registrado,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return AprobacionResultado(
            solicitud=solicitud,
            productos_actualizados=productos_actualizados,
            unidades_agregadas=unidades_agregadas,
            monto_total=monto_total,
            credito_registrado=credito_registrado,
            productos_creados=productos_creados,
        )
