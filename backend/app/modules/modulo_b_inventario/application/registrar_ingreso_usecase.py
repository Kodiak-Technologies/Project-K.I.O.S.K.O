# Caso de uso: registrar una solicitud de ingreso de mercadería (HU-B05/06, REQ-ING).
# - La foto de la boleta es OPCIONAL (cadena vacía = sin foto).
# - Valida líneas (>=1, cada una con cantidad>0 y precio>=0).
# - Valida productos y proveedor (opcional) existen.
# - INSERT solicitud + detalles en una sola tx.
# - NO toca stock.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    DetalleSolicitud,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


@dataclass
class LineaSolicitudDTO:
    """Una línea de la boleta.

    O apunta a un producto del catálogo (`producto_id`), o describe uno que
    todavía no existe (`nuevo_*`). El segundo caso es el que evita que el
    cajero tenga que pedirle a un ADMIN que dé de alta el producto antes de
    poder transcribir la boleta: el producto se crea al aprobar.

    `precio_compra_total` es el monto de la línea tal cual figura en la boleta
    ("7 esponjas — S/ 20"), NO el unitario.
    """

    cantidad: int
    precio_compra_total: Decimal
    producto_id: int | None = None
    nuevo_codigo: str | None = None
    nuevo_nombre: str | None = None
    nuevo_categoria_id: int | None = None

    @property
    def es_producto_nuevo(self) -> bool:
        return self.producto_id is None


class RegistrarIngresoUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        detalle_repo: DetalleSolicitudRepositoryPort,
        producto_repo: ProductoRepositoryPort,
        proveedor_repo: ProveedorRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
        notificador=None,
    ):
        self._solicitudes = solicitud_repo
        self._detalles = detalle_repo
        self._productos = producto_repo
        self._proveedores = proveedor_repo
        self._auditoria = auditoria
        # Opcional para los tests unitarios; el contenedor siempre lo inyecta.
        self._notificador = notificador

    async def ejecutar(
        self,
        *,
        proveedor_id: int | None,
        lineas: list[LineaSolicitudDTO],
        usuario_id: int,
        usuario_nombre: str,
        #: Opcional: no toda compra viene con boleta, y frenar la carga por eso
        #: dejaba mercadería sin registrar. Cadena vacía = sin foto.
        foto_boleta_url: str = "",
        ip: str = "",
        user_agent: str = "",
    ) -> SolicitudIngreso:
        if not lineas:
            raise ValidacionError("La solicitud debe tener al menos una línea.")
        codigos_nuevos: set[str] = set()
        for idx, l in enumerate(lineas, start=1):
            if l.cantidad is None or l.cantidad <= 0:
                raise ValidacionError(
                    f"La línea {idx} tiene una cantidad inválida (debe ser > 0)."
                )
            if l.precio_compra_total is None or l.precio_compra_total < 0:
                raise ValidacionError(
                    f"La línea {idx} tiene un total inválido (debe ser >= 0)."
                )
            if not l.es_producto_nuevo:
                p = await self._productos.buscar_por_id(l.producto_id)
                if p is None or p.deleted_at is not None:
                    raise NoEncontradoError(
                        f"El producto de la línea {idx} no existe."
                    )
                continue

            # Producto propuesto: se valida acá lo que se pueda, para no hacerle
            # perder el trabajo al cajero recién al momento de aprobar.
            codigo = (l.nuevo_codigo or "").strip()
            nombre = (l.nuevo_nombre or "").strip()
            if not codigo or not nombre:
                raise ValidacionError(
                    f"La línea {idx} es un producto nuevo: falta el código de "
                    "barras o el nombre."
                )
            if codigo in codigos_nuevos:
                raise ValidacionError(
                    f"El código '{codigo}' está repetido en más de una línea."
                )
            codigos_nuevos.add(codigo)
            existente = await self._productos.buscar_por_codigo(codigo)
            if existente is not None and existente.deleted_at is None:
                raise ValidacionError(
                    f"El código '{codigo}' ya pertenece a '{existente.nombre}'. "
                    "Elige ese producto del catálogo en vez de crearlo de nuevo."
                )

        if proveedor_id is not None:
            prov = await self._proveedores.find_by_id(proveedor_id)
            if prov is None or prov.deleted_at is not None:
                raise NoEncontradoError("El proveedor no existe.")

        solicitud = await self._solicitudes.crear(
            SolicitudIngreso(
                id=None,
                estado=EstadoSolicitud("Pendiente"),
                foto_boleta_url=(foto_boleta_url or "").strip(),
                solicitado_por=usuario_id,
                solicitado_por_nombre=usuario_nombre,
                proveedor_id=proveedor_id,
            )
        )
        detalles = [
            DetalleSolicitud(
                id=None,
                solicitud_id=solicitud.id,  # type: ignore[arg-type]
                producto_id=l.producto_id,
                cantidad=l.cantidad,
                precio_compra_total=l.precio_compra_total,
                nuevo_codigo=(l.nuevo_codigo or "").strip() or None,
                nuevo_nombre=(l.nuevo_nombre or "").strip() or None,
                nuevo_categoria_id=l.nuevo_categoria_id,
            )
            for l in lineas
        ]
        await self._detalles.crear_bulk(detalles)
        completa = await self._solicitudes.find_by_id(solicitud.id)  # type: ignore[arg-type]

        await self._auditoria.ejecutar(
            accion="ingreso_solicitado",
            entidad="solicitudes_ingreso",
            usuario_id=usuario_id,
            rol="",
            entidad_id=solicitud.id,
            valor_nuevo={
                "proveedor_id": proveedor_id,
                "cantidad_productos": len(lineas),
                # Suma de los totales de línea: son el dato de la boleta. Volver
                # a multiplicar por cantidad daría un monto inventado.
                "monto_total": float(
                    sum((l.precio_compra_total for l in lineas), start=Decimal("0"))
                ),
                "productos_nuevos": sum(1 for l in lineas if l.es_producto_nuevo),
            },
            ip=ip,
            user_agent=user_agent,
        )

        # HU-B06: la administradora tiene que enterarse de que hay algo por
        # aprobar sin depender de que entre a mirar la pantalla.
        if self._notificador is not None:
            from app.modules.modulo_d_documentos.domain.value_objects import (
                TipoNotificacion,
            )

            unidades = sum(l.cantidad for l in lineas)
            monto = sum((l.precio_compra_total for l in lineas), start=Decimal("0"))
            nuevos = sum(1 for l in lineas if l.es_producto_nuevo)
            # Que se vea en el aviso: si hay productos nuevos, aprobar implica
            # además darlos de alta en el catálogo.
            aviso_nuevos = (
                f" Incluye {nuevos} producto(s) que se van a crear en el catálogo."
                if nuevos
                else ""
            )
            await self._notificador.avisar(
                TipoNotificacion.SOLICITUD_INGRESO,
                f"Ingreso pendiente de aprobación (#{solicitud.id})",
                f"{usuario_nombre} registró {len(lineas)} producto(s) "
                f"({unidades} unidades) por S/ {float(monto):.2f}.{aviso_nuevos} "
                "Queda pendiente hasta que lo apruebes.",
                entidad_origen="solicitudes_ingreso",
                entidad_id=solicitud.id,
            )
        return completa  # type: ignore[return-value]
