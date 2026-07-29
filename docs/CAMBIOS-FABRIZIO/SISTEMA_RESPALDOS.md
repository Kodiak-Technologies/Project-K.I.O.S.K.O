# Sistema de Respaldos y Restauración — Cambios

**Autor:** Fabrizio
**Fecha:** 27 julio 2026
**Branch:** `modulo-d/restore-fix`

## Resumen

Implementación completa del sistema de respaldo automático diario con subida a Google Drive, y script standalone de restauración. Se resolvieron problemas de FK constraints, secuencias vacías y tablas preservadas durante el restore.

## 1. Arquitectura del sistema

### 1.1 Generación de respaldo

**Archivo:** `modules/modulo_d_documentos/application/crear_respaldo_usecase.py`

El respaldo genera un archivo `.sql` válido (sin `pg_dump`) usando `asyncpg` directo:

```
1. Consultar todas las tablas de TABLAS_ORDEN (22 tablas)
2. Para cada tabla: SELECT * → escape de valores → generar INSERT
3. Para usuarios: INSERT sin deleted_by → UPDATE para restaurar self-referencing FK
4. Generar DELETEs en orden inverso de FK (hijos antes que padres)
5. Generar INSERTs en orden normal (padres antes que hijos)
6. Generar SETVAL para todas las secuencias
7. Subir a Google Drive en respaldos/YYYY/MM/
8. Registrar en tabla respaldos
```

**Orden de tablas (TABLAS_ORDEN):**
```python
# Modulo A — seguridad
"roles", "permisos", "rol_permisos", "usuarios", "sesiones",
"bitacora_auditoria", "configuracion_negocio",
# Modulo B — inventario
"categorias", "proveedores", "productos", "solicitudes_ingreso",
"detalle_solicitud", "pagos_proveedor", "movimientos_inventario",
"historial_precios",
# Modulo C — ventas y caja
"metodos_pago", "turnos_caja", "arqueos", "ventas", "detalles_venta",
"pagos_venta", "anulaciones",
# Modulo D — documentos
"notificaciones", "config_notificaciones", "respaldos", "oauth_tokens",
```

### 1.2 Restauración

**Archivo:** `scripts/restaurar_respaldo.py` (standalone, fuera del API)

```
1. Conectar a BD + Google Drive (refrescar token si expiró)
2. Listar archivos .sql disponibles en Drive
3. Seleccionar archivo (CLI o interactivo)
4. Descargar contenido
5. Ejecutar restore dentro de transacción:
   a. BEGIN
   b. Deshabilitar triggers de inmutabilidad
   c. Limpiar FK autorreferencial (usuarios.deleted_by)
   d. DELETE todas las tablas (orden inverso, excepto respaldos)
   e. SET session_replication_role = 'replica' (deshabilitar FKs)
   f. Ejecutar INSERTs del archivo .sql
   g. SET session_replication_role = 'origin' (rehabilitar FKs)
   h. COMMIT (o ROLLBACK si falla)
   i. Rehabilitar triggers
```

### 1.3 Respaldo automático

**Archivo:** `modules/modulo_d_documentos/infrastructure/tasks/respaldos_automatico.py`

- Se ejecuta diariamente a las 3:00 AM (hora de Perú)
- Crea respaldo + sube a Drive + limpia respaldos expirados (>4 días)
- Retención: 4 días (hardcoded)

## 2. Problemas resueltos

### 2.1 FK constraint violation al restaurar

**Error:** `insert or update on table "bitacora_auditoria" violates foreign key constraint "bitacora_auditoria_usuario_id_fkey" — Key (usuario_id)=(59) is not present in table "usuarios"`

**Causa:** Datos inconsistentes en el backup (bitacora_auditoria referencia usuarios que no existen en el backup).

**Solución:** Deshabilitar todas las FK constraints durante la fase de INSERT:
```python
await conn.execute("SET session_replication_role = 'replica'")
# ... ejecutar INSERTs ...
await conn.execute("SET session_replication_role = 'origin'")
```

### 2.2 setval con valor 0

**Error:** `setval: value 0 is out of bounds for sequence "turnos_caja_id_seq"`

**Causa:** Backups de tablas vacías generan `SELECT setval('seq', 0)`.

**Solución:** Filtrar sentencias setval con valor 0:
```python
if linea.upper().startswith("SELECT SETVAL(") and ", 0)" in linea:
    continue
```

### 2.3 Conflicto con tabla respaldos

**Error:** `duplicate key value violates unique constraint "respaldos_pkey" — Key (id)=(24) already exists`

**Causa:** El backup incluye INSERTs de la tabla `respaldos`, pero el restore la preserva intencionalmente (no la borra).

**Solución:** Saltar INSERTs y SETVAL de `respaldos`:
```python
if "INSERT INTO" in linea.upper() and '"respaldos"' in linea:
    continue
if linea.upper().startswith("SELECT SETVAL(") and '"respaldos_id_seq"' in linea:
    continue
```

### 2.4 Self-referencing FK (usuarios.deleted_by)

**Problema:** `usuarios.deleted_by` referencia a la misma tabla. No se puede INSERT con esa columna.

**Solución en generación:** INSERT sin `deleted_by`, luego UPDATE para restaurar valores.
**Solución en restore:** `UPDATE usuarios SET deleted_by = NULL` antes de DELETE.

### 2.5 Triggers de inmutabilidad

**Problema:** `bitacora_auditoria` y `historial_precios` tienen triggers que bloquean UPDATE/DELETE.

**Solución:** Deshabilitar triggers antes del restore, rehabilitar después:
```python
await conn.execute("ALTER TABLE bitacora_auditoria DISABLE TRIGGER trg_bitacora_inmutable")
await conn.execute("ALTER TABLE historial_precios DISABLE TRIGGER trg_historial_precios_no_update")
```

## 3. Uso del script de restauración

### Modo interactivo
```bash
cd backend
python -m scripts.restaurar_respaldo
```
Lista archivos de Drive, pide nombre, confirma, restaura.

### Modo directo (sin confirmar)
```bash
python -m scripts.restaurar_respaldo tienda_sistema_20260727_043605.sql
```
Selecciona automáticamente el archivo y restaura sin pedir confirmación.

### Requisitos
- `.env` con `DATABASE_URL`, `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`
- Tokens de Drive en tabla `oauth_tokens` (autorizar via `GET /drive/auth-url`)
- Conexión a la BD (asyncpg directo, statement_cache_size=0)

## 4. Endpoints relacionados

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/respaldos` | Listar respaldos |
| POST | `/respaldos` | Crear respaldo manual |
| GET | `/respaldos/{id}/descargar` | Descargar .sql desde Drive |
| GET | `/drive/auth-url` | Obtener URL de autorización OAuth |
| GET | `/drive/callback` | Callback de OAuth |
| GET | `/drive/status` | Estado de conexión con Drive |

## 5. Archivos modificados/creados

| Acción | Archivo |
|--------|---------|
| **Modificar** | `scripts/restaurar_respaldo.py` — fix FK, setval, respaldos skip, CLI |
| **Crear** | `scripts/listar_respaldos.py` — helper para listar respaldos |
| **Modificar** | `modules/modulo_d_documentos/application/crear_respaldo_usecase.py` — eliminado RestaurarRespaldoUseCase |
| **Modificar** | `modules/modulo_d_documentos/infrastructure/http/respaldos_router.py` — eliminado endpoint restaurar |
| **Modificar** | `modules/modulo_d_documentos/module_container.py` — eliminado wiring de restore |

## 6. Decisions

| Decisión | Justificación |
|----------|---------------|
| Script standalone vs endpoint | Restore es operación destructiva, mejor fuera del API |
| session_replication_role vs ALTER TABLE individual | Más simple, desactiva todas las FK de una vez |
| Filtrar setval(0) | Tablas vacías generan setval inválido |
| Preservar respaldos durante restore | No perder historial de respaldos anteriores |
| CLI sin confirmación | Para automatización y testing |
