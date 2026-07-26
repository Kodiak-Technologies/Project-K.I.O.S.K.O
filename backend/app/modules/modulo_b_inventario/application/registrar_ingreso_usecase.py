# Caso de uso: registrar una solicitud de ingreso de mercadería (HU-B05/06, REQ-ING).
# - Valida foto_boleta_url no vacía.
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
    producto_id: int
    cantidad: int
    precio_compra_unitario: Decimal


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
        foto_boleta_url: str,
        lineas: list[LineaSolicitudDTO],
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> SolicitudIngreso:
        if not foto_boleta_url or not foto_boleta_url.strip():
            raise ValidacionError(
                "Debes adjuntar la foto de la boleta para enviar la solicitud."
            )
        if not lineas:
            raise ValidacionError("La solicitud debe tener al menos una línea.")
        for idx, l in enumerate(lineas, start=1):
            if l.cantidad is None or l.cantidad <= 0:
                raise ValidacionError(
                    f"La línea {idx} tiene una cantidad inválida (debe ser > 0)."
                )
            if l.precio_compra_unitario is None or l.precio_compra_unitario < 0:
                raise ValidacionError(
                    f"La línea {idx} tiene un precio inválido (debe ser >= 0)."
                )
            p = await self._productos.buscar_por_id(l.producto_id)
            if p is None or p.deleted_at is not None:
                raise NoEncontradoError(
                    f"El producto de la línea {idx} no existe."
                )

        if proveedor_id is not None:
            prov = await self._proveedores.find_by_id(proveedor_id)
            if prov is None or prov.deleted_at is not None:
                raise NoEncontradoError("El proveedor no existe.")

        solicitud = await self._solicitudes.crear(
            SolicitudIngreso(
                id=None,
                estado=EstadoSolicitud("Pendiente"),
                foto_boleta_url=foto_boleta_url.strip(),
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
                precio_compra_unitario=l.precio_compra_unitario,
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
                "monto_total": float(
                    sum(
                        (l.cantidad * l.precio_compra_unitario for l in lineas),
                        start=Decimal("0"),
                    )
                ),
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
            monto = sum(
                (l.cantidad * l.precio_compra_unitario for l in lineas),
                start=Decimal("0"),
            )
            await self._notificador.avisar(
                TipoNotificacion.SOLICITUD_INGRESO,
                f"Ingreso pendiente de aprobación (#{solicitud.id})",
                f"{usuario_nombre} registró {len(lineas)} producto(s) "
                f"({unidades} unidades) por S/ {float(monto):.2f}. "
                "Queda pendiente hasta que lo apruebes.",
                entidad_origen="solicitudes_ingreso",
                entidad_id=solicitud.id,
            )
        return completa  # type: ignore[return-value]
