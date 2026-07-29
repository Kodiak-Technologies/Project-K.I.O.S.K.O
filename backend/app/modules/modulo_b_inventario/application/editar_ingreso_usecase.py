"""Caso de uso: editar una SolicitudIngreso en estado Pendiente.

Pre-condiciones (sdd/modulo-b-aprobaciones-detalle-editar, FR-3):
  - Estado == Pendiente (si no, 409 NOT_EDITABLE_STATE).
  - Usuario es ADMIN o el creador (sino, 403 FORBIDDEN).
  - Body con al menos un campo editable (sino, 422 EMPTY_PATCH).
  - Si vienen `proveedor_id` / `producto_id`, el FK debe existir (sino, 422).
  - `lineas[].cantidad > 0` y `lineas[].precio_unitario >= 0` (sino, 422).

Transacción:
  1. `solicitud_repo.find_by_id_for_update(id)` (FOR UPDATE lock).
  2. `solicitud.editar(...)` → cambios de cabecera + nuevas lineas.
  3. Si vienen lineas: `detalle_repo.eliminar_por_solicitud` + `detalle_repo.crear_bulk`.
  4. `solicitud_repo.actualizar_cabecera(id, cambios)` (escribe audit triple + updated_at).
  5. `auditoria.ejecutar(accion="editar_ingreso", ..., valor_anterior, valor_nuevo)`.

Post: la entidad devuelta incluye `lineas` recargadas y `editado_*` seteados.
"""
from __future__ import annotations

from typing import Any

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import DetalleSolicitud
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.shared.kernel.exceptions import (
    NoEncontradoError,
    ProhibidoError,
    ValidacionError,
)


class EditarIngresoUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        detalle_repo: DetalleSolicitudRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
        producto_repo=None,
        proveedor_repo=None,
    ):
        self._solicitudes = solicitud_repo
        self._detalles = detalle_repo
        self._auditoria = auditoria
        # Opcionales solo para los tests unitarios con mocks; el contenedor
        # siempre los inyecta y sin ellos no se validan las FKs.
        self._productos = producto_repo
        self._proveedores = proveedor_repo

    async def ejecutar(
        self,
        *,
        ingreso_id: int,
        editor_id: int,
        editor_nombre: str,
        es_admin: bool,
        proveedor_id: int | None = ...,
        motivo: str | None = ...,
        foto_boleta_url: str | None = ...,
        lineas: list[dict] | None = ...,
        ip: str = "",
        user_agent: str = "",
    ) -> Any:  # returns SolicitudIngreso
        """lineas: list of dicts con {cantidad, precio_compra_total} y, o bien
        `producto_id`, o bien `nuevo_codigo`/`nuevo_nombre` para un producto a
        crear al aprobar. `margen_ganancia` es opcional. None = no tocar."""

        # 1. EMPTY_PATCH check (FR-3.3.2)
        if all(
            v is ...
            for v in (proveedor_id, motivo, foto_boleta_url, lineas)
        ):
            raise ValidacionError(
                "Debes enviar al menos un campo para editar.",
                code="EMPTY_PATCH",
            )

        # 2. Lineas value validation (Pydantic ya valida formato; acá solo
        #    verificamos FKs que el use case no puede confiar del todo).
        lineas_payload: list[dict] | None = None
        if lineas is not ... and lineas is not None:
            lineas_payload = []
            for idx, l in enumerate(lineas, start=1):
                cant = l.get("cantidad")
                precio = l.get("precio_compra_total")
                if cant is None or precio is None:
                    raise ValidacionError(
                        f"Línea {idx}: cantidad y precio_compra_total son obligatorios.",
                        code="INVALID_LINE_VALUES",
                    )
                pid = l.get("producto_id")
                codigo = (l.get("nuevo_codigo") or "").strip()
                nombre = (l.get("nuevo_nombre") or "").strip()
                if pid is None and not (codigo and nombre):
                    raise ValidacionError(
                        f"Línea {idx}: indica un producto del catálogo o el código "
                        "y nombre del producto nuevo.",
                        code="INVALID_LINE_VALUES",
                    )
                lineas_payload.append(
                    {
                        "producto_id": int(pid) if pid is not None else None,
                        "cantidad": int(cant),
                        "precio_compra_total": precio,
                        "nuevo_codigo": codigo or None,
                        "nuevo_nombre": nombre or None,
                        "nuevo_categoria_id": l.get("nuevo_categoria_id"),
                        "margen_ganancia": l.get("margen_ganancia"),
                    }
                )

        # 2.b Validación de FKs ANTES de tocar nada: sin esto un producto_id o
        #     proveedor_id inexistente llegaba al INSERT y Postgres respondía
        #     con violación de FK (500) en vez de un 422 entendible.
        if proveedor_id is not ... and proveedor_id is not None and self._proveedores:
            prov = await self._proveedores.find_by_id(proveedor_id)
            if prov is None:
                raise ValidacionError(
                    "El proveedor indicado no existe.", code="PROVEEDOR_NOT_FOUND"
                )
        if lineas_payload and self._productos:
            for idx, l in enumerate(lineas_payload, start=1):
                pid = l["producto_id"]
                if pid is None:
                    # Producto a crear: no hay FK que validar todavía, pero sí
                    # que el código no esté ya tomado (si no, la aprobación
                    # reventaría después de que la admin ya la dio por buena).
                    codigo = l["nuevo_codigo"]
                    existente = await self._productos.buscar_por_codigo(codigo)
                    if existente is not None and existente.deleted_at is None:
                        raise ValidacionError(
                            f"Línea {idx}: el código '{codigo}' ya pertenece a "
                            f"'{existente.nombre}'. Elígelo del catálogo.",
                            code="CODIGO_DUPLICADO",
                        )
                    continue
                producto = await self._productos.buscar_por_id(pid)
                if producto is None or producto.deleted_at is not None:
                    raise ValidacionError(
                        f"Línea {idx}: el producto {pid} no existe.",
                        code="PRODUCTO_NOT_FOUND",
                    )

        # 3. FOR UPDATE lock
        solicitud = await self._solicitudes.find_by_id_for_update(ingreso_id)
        if solicitud is None:
            raise NoEncontradoError(
                "La solicitud no existe o fue eliminada.",
                code="INGRESO_NOT_FOUND",
            )

        # 4. Permission + state guard (entity raises with the right code)
        #    (también lo verifica el route-level, pero acá es defensa en profundidad).
        if not solicitud.puede_ser_editada_por(editor_id, es_admin):
            # Distinguish state vs permission in the error
            from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud
            if solicitud.estado != EstadoSolicitud("Pendiente") or solicitud.eliminado:
                # Re-raise with the right code via a fresh call
                solicitud.editar(  # will raise ConflictoError code=NOT_EDITABLE_STATE
                    editor_id=editor_id,
                    editor_nombre=editor_nombre,
                    es_admin=es_admin,
                )
            else:
                solicitud.editar(  # will raise ProhibidoError code=FORBIDDEN
                    editor_id=editor_id,
                    editor_nombre=editor_nombre,
                    es_admin=es_admin,
                )

        # 5. Snapshot for audit (before mutation)
        cabecera_anterior: dict = {
            "proveedor_id": solicitud.proveedor_id,
            "motivo": solicitud.motivo,
            "foto_boleta_url": solicitud.foto_boleta_url,
        }
        lineas_anteriores: list[dict] = [
            {
                "producto_id": l.producto_id,
                "producto": l.descripcion,
                "cantidad": l.cantidad,
                "precio_compra_total": float(l.precio_compra_total),
            }
            for l in solicitud.lineas
        ]

        # 6. Entity mutation
        cambios, nuevas_lineas = solicitud.editar(
            editor_id=editor_id,
            editor_nombre=editor_nombre,
            es_admin=es_admin,
            proveedor_id=proveedor_id,
            motivo=motivo,
            foto_boleta_url=foto_boleta_url,
            lineas_payload=lineas_payload,
        )

        # 7. Persist lineas if changed
        if nuevas_lineas is not None:
            await self._detalles.eliminar_por_solicitud(ingreso_id)
            if nuevas_lineas:
                # Set solicitud_id on the new DetalleSolicitud rows
                for l in nuevas_lineas:
                    l.solicitud_id = ingreso_id
                await self._detalles.crear_bulk(nuevas_lineas)
            # Mantener la entidad en memoria consistente con la BD
            solicitud.lineas = nuevas_lineas

        # 8. Persist cabecera (escribe audit triple + updated_at via el server-side)
        await self._solicitudes.actualizar_cabecera(ingreso_id, cambios)

        # 9. Audit
        cabecera_nueva: dict = {
            "proveedor_id": solicitud.proveedor_id,
            "motivo": solicitud.motivo,
            "foto_boleta_url": solicitud.foto_boleta_url,
        }
        await self._auditoria.ejecutar(
            accion="editar_ingreso",
            entidad="solicitudes_ingreso",
            usuario_id=editor_id,
            rol="",
            entidad_id=ingreso_id,
            motivo=(motivo if motivo is not ... else None) or "",
            ip=ip,
            user_agent=user_agent,
            valor_anterior={
                "cabecera": cabecera_anterior,
                "lineas": lineas_anteriores,
            },
            valor_nuevo={
                "cabecera": cabecera_nueva,
                "lineas": [
                    {
                        "producto_id": l.producto_id,
                        "producto": l.descripcion,
                        "cantidad": l.cantidad,
                        "precio_compra_total": float(l.precio_compra_total),
                    }
                    for l in nuevas_lineas
                ]
                if nuevas_lineas is not None
                else lineas_anteriores,
            },
        )

        # 10. Refrescar (re-cargar con las lineas finales)
        return await self._solicitudes.find_by_id(ingreso_id)
