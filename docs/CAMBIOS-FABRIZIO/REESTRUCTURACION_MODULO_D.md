# Cambios Módulo D — Documentos

**Autor:** Fabrizio
**Fecha:** 22 julio 2026
**Branch:** `feature/modulo_d_documentos`

## Resumen de cambios

Reestructuración completa del Módulo D: eliminación de tablas `boletas_clientes` y `archivos_drive`, reemplazo de "Boletas" por "Notas de Venta" generadas on-the-fly, simplificación de `config_notificaciones`, FK cross-module a `usuarios`, batch download/upload de PNGs.

## Decisiones clave

| Decisión | Justificación |
|----------|---------------|
| Eliminar `boletas_clientes` | Las notas se generan via SQL contra `ventas` + `detalles_venta` |
| Eliminar `archivos_drive` | No se necesitan registros de estado; subida directa a Drive |
| Nota de venta = query on-the-fly | Identificación: `YYYY-MM-DD_VENTA-{id}` |
| Sin campo cliente en notas | RF-21 no lo requiere para notas internas |
| Sin conexión SUNAT | Pendiente para futuro |
| PNG generado en backend | Consistencia con formato ticket POS |
| Download/upload por batch | Selección de rango → generar → ZIP o Drive |
| Config simplificada | Solo `nivel_detalle`; Telegram/Correo en `.env` |
| FK `notificaciones.usuario_id` | Per-user notifications, nullable SET NULL |
| Columna `producto_id` en notificaciones | Para notificaciones STOCK_BAJO |
| Marcar leída al ver | Automático en campanita y página notificaciones |

## Archivos modificados/creados/eliminados

### Backend

| Acción | Archivo |
|--------|---------|
| **Crear** | `alembic/versions/0012_modulo_d_reestructuracion.py` |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/adapters/database/models.py` |
| **Modificar** | `modules/modulo_d_documentos/domain/entities.py` |
| **Modificar** | `modules/modulo_d_documentos/domain/value_objects.py` |
| **Modificar** | `modules/modulo_d_documentos/domain/ports/notificacion_repository_port.py` |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/adapters/database/sqlalchemy_notificacion_repository.py` |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/adapters/database/sqlalchemy_config_notificaciones_repository.py` |
| **Crear** | `modules/modulo_d_documentos/application/generar_nota_venta_usecase.py` |
| **Crear** | `modules/modulo_d_documentos/application/descargar_notas_venta_usecase.py` |
| **Crear** | `modules/modulo_d_documentos/application/subir_notas_drive_usecase.py` |
| **Crear** | `modules/modulo_d_documentos/application/marcar_notificacion_leida_usecase.py` |
| **Crear** | `modules/modulo_d_documentos/application/marcar_todas_notificaciones_leidas_usecase.py` |
| **Crear** | `modules/modulo_d_documentos/application/eliminar_notificaciones_expiradas_usecase.py` |
| **Modificar** | `modules/modulo_d_documentos/application/enviar_notificacion_usecase.py` |
| **Renombrar** | `boleta_png_generator.py` → `nota_venta_png_generator.py` |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/http/schemas.py` |
| **Crear** | `modules/modulo_d_documentos/infrastructure/http/notas_venta_router.py` |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/http/notificaciones_router.py` |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/dependencies.py` |
| **Modificar** | `modules/modulo_d_documentos/module_container.py` |
| **Eliminar** | `modules/modulo_d_documentos/domain/ports/boleta_repository_port.py` |
| **Eliminar** | `modules/modulo_d_documentos/domain/ports/archivo_drive_repository_port.py` |
| **Eliminar** | `modules/modulo_d_documentos/infrastructure/adapters/database/sqlalchemy_boleta_repository.py` |
| **Eliminar** | `modules/modulo_d_documentos/infrastructure/adapters/database/sqlalchemy_archivo_drive_repository.py` |
| **Eliminar** | `modules/modulo_d_documentos/application/generar_boleta_usecase.py` |
| **Eliminar** | `modules/modulo_d_documentos/application/subir_boleta_drive_usecase.py` |
| **Eliminar** | `modules/modulo_d_documentos/infrastructure/http/boletas_router.py` |
| **Eliminar** | `modules/modulo_d_documentos/infrastructure/tasks/reintentar_subidas.py` |

### Frontend

| Acción | Archivo |
|--------|---------|
| **Modificar** | `modules/modulo-d-documentos/types/index.ts` |
| **Crear** | `modules/modulo-d-documentos/services/notasVenta.port.ts` |
| **Crear** | `modules/modulo-d-documentos/services/notasVenta.http-adapter.ts` |
| **Crear** | `modules/modulo-d-documentos/hooks/useNotasVenta.ts` |
| **Crear** | `modules/modulo-d-documentos/pages/NotasDeVenta.tsx` |
| **Modificar** | `modules/modulo-d-documentos/routes.tsx` |
| **Modificar** | `modules/modulo-d-documentos/pages/Notificaciones.tsx` |
| **Modificar** | `modules/modulo-d-documentos/services/notificaciones.port.ts` |
| **Modificar** | `modules/modulo-d-documentos/services/notificaciones.http-adapter.ts` |
| **Modificar** | `shared/components/Sidebar.tsx` |
| **Modificar** | `shared/components/ui/Button.tsx` (whitespace-nowrap) |
| **Eliminar** | `modules/modulo-d-documentos/pages/Boletas.tsx` |
| **Eliminar** | `modules/modulo-d-documentos/hooks/useBoletas.ts` |
| **Eliminar** | `modules/modulo-d-documentos/services/boletas.port.ts` |
| **Eliminar** | `modules/modulo-d-documentos/services/boletas.http-adapter.ts` |

## Endpoints nuevos/modificados

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/notas-venta` | Listar notas de venta (consulta SQL) |
| GET | `/notas-venta/{venta_id}/png` | Descargar PNG de una nota |
| POST | `/notas-venta/descargar` | Batch download (ZIP si >1 venta) |
| POST | `/notas-venta/subir-drive` | Batch upload a Google Drive |
| POST | `/notificaciones/leer-todas` | Marcar todas como leídas |
| GET | `/notificaciones` | Listar por usuario (no leídas primero) |

## Migración

```bash
alembic upgrade head
```

La migración `0012_modulo_d_reestructuracion.py`:
- Elimina tablas `boletas_clientes` y `archivos_drive`
- Simplifica `config_notificaciones` (elimina columnas de telegram/correo)
- Agrega FK `notificaciones.usuario_id` → `usuarios.id` (nullable, SET NULL)
- Agrega columna `notificaciones.producto_id`

## Commits

```
2d19af3 modulo-d: migracion Alembic — eliminar boletas_clientes, archivos_drive, simplificar config
c081e8e modulo-d: eliminar models/entities boletas, simplificar config_notificaciones, agregar VentaResumen
007c62a modulo-d: eliminar repos de boleta/archivo_drive, agregar listar_por_usuario y marcar_todas_leidas
f257616 modulo-d: crear use cases notas de venta, notificacion leida, eliminar expiradas
afc4284 modulo-d: renombrar BoletaPngGenerator a NotaVentaPngGenerator, formato Nota de Venta
bd63a08 modulo-d: schemas — eliminar BoletaResponse/ArchivoDriveResponse, agregar NotaVentaResponse, simplificar config
3008827 modulo-d: crear notas_venta_router, eliminar boletas_router, actualizar notificaciones_router con usuario_id y marcar_todas_leidas
141885e modulo-d: actualizar dependencies y module_container, eliminar reintentar_subidas.py obsoleto
16e502d modulo-d frontend: renombrar Boletas a NotasDeVenta, agregar batch download/upload, fix button distortion, campanita leer-todas
```
