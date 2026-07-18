# Diagrama Entidad-Relación — Módulo D (Documentos)

**Módulo**: Documentos (Boletas/Drive), Reportes, Notificaciones e Infraestructura
**Base de datos**: PostgreSQL 16
**Zona horaria**: America/Lima

---

## Diagrama Mermaid

```mermaid
erDiagram
    boletas_clientes {
        BIGINT id PK
        BIGINT venta_id FK "UNIQUE → ventas.id (Module C)"
        VARCHAR(20) numero "UNIQUE, INDEX — formato B001-NNNNNN"
        NUMERIC total "monto total de la venta"
        VARCHAR(120) cliente_nombre "nombre del cliente (default: Cliente 1)"
        TIMESTAMPTZ emitida_en "DEFAULT NOW()"
        TEXT url_pdf "nullable — URL en Google Drive"
    }

    archivos_drive {
        BIGINT id PK
        BIGINT boleta_id FK "→ boletas_clientes.id"
        VARCHAR(255) archivo_nombre "nombre del archivo subido"
        VARCHAR(255) carpeta "ej: boletas/2026/07/"
        VARCHAR(20) estado "PENDIENTE | SUBIDO | FALLIDO"
        INT intentos "DEFAULT 0"
        VARCHAR(255) drive_file_id "nullable — ID en Google Drive"
        TEXT error_mensaje "nullable — último error"
        TIMESTAMPTZ creado_en "DEFAULT NOW()"
        TIMESTAMPTZ actualizado_en "DEFAULT NOW()"
    }

    notificaciones {
        BIGINT id PK
        VARCHAR(30) tipo "STOCK_BAJO | CIERRE_CAJA | SOLICITUD_INGRESO"
        VARCHAR(120) titulo "título de la notificación"
        TEXT mensaje "cuerpo del mensaje"
        BOOLEAN leida "DEFAULT FALSE"
        VARCHAR(60) entidad_origen "nullable — tabla origen"
        VARCHAR(60) entidad_id "nullable — ID de la entidad origen"
        BIGINT usuario_id FK "nullable → usuarios.id (Module A)"
        TIMESTAMPTZ created_at "DEFAULT NOW()"
    }

    config_notificaciones {
        INT id PK "siempre 1 (fila única)"
        BOOLEAN canal_telegram_activo "DEFAULT TRUE"
        BOOLEAN canal_correo_activo "DEFAULT FALSE"
        VARCHAR(20) nivel_detalle "BAJO | MEDIO | ALTO"
        VARCHAR(100) telegram_chat_id "nullable"
        VARCHAR(120) correo_destino "nullable"
        TIMESTAMPTZ updated_at "DEFAULT NOW()"
    }

    respaldos {
        BIGINT id PK
        VARCHAR(255) archivo_nombre "ej: tienda_sistema_20260714_020000.dump"
        BIGINT tamano_bytes "tamaño del archivo"
        VARCHAR(20) estado "PENDIENTE | COMPLETADO | FALLIDO"
        TIMESTAMPTZ generado_en "DEFAULT NOW()"
        TIMESTAMPTZ expira_en "DEFAULT now() + 30 días"
    }

    oauth_tokens {
        BIGINT id PK
        VARCHAR(50) proveedor "google_drive"
        TEXT access_token "token temporal (expira en 1 hora)"
        TEXT refresh_token "token para renovar (nunca expira)"
        TIMESTAMPTZ token_expiry "cuándo expira el access_token"
        BIGINT usuario_id FK "nullable → usuarios.id (Module A)"
        TIMESTAMPTZ fecha_creacion "DEFAULT NOW()"
        TIMESTAMPTZ fecha_actualizacion "DEFAULT NOW()"
    }

    %% Relaciones externas (fuera de Module D)
    ventas ||--o| boletas_clientes : "tiene una boleta"
    usuarios ||--o| notificaciones : "puede recibir"
    usuarios ||--o| oauth_tokens : "autoriza Drive"

    %% Relaciones internas de Module D
    boletas_clientes ||--o| archivos_drive : "se sube a Drive"
    boletas_clientes ||--o| notificaciones : "puede generar"
```

---

## Tablas resumen

| Tabla | PK | FK | Descripción |
|-------|----|----|-------------|
| `boletas_clientes` | `id` (BIGINT) | `venta_id` → `ventas.id` (Module C) | Boletas digitales generadas |
| `archivos_drive` | `id` (BIGINT) | `boleta_id` → `boletas_clientes.id` | Control de subida a Google Drive |
| `notificaciones` | `id` (BIGINT) | `usuario_id` → `usuarios.id` (Module A) | Notificaciones del sistema |
| `config_notificaciones` | `id` (INT, siempre 1) | — | Configuración de canales |
| `respaldos` | `id` (BIGINT) | — | Registro de copias de seguridad |
| `oauth_tokens` | `id` (BIGINT) | `usuario_id` → `usuarios.id` (Module A) | Tokens OAuth para Google Drive |

---

## Cardinalidades

| Relación | Tipo | Descripción |
|----------|------|-------------|
| `ventas` → `boletas_clientes` | 1:0..1 | Una venta puede tener una boleta (o ninguna si aún no se genera) |
| `boletas_clientes` → `archivos_drive` | 1:0..1 | Una boleta se sube a Drive (o pendiente) |
| `boletas_clientes` → `notificaciones` | 1:0..N | Una boleta puede generar notificaciones |
| `usuarios` → `notificaciones` | 1:0..N | Un usuario puede recibir muchas notificaciones |
| `usuarios` → `oauth_tokens` | 1:0..1 | Un usuario autoriza Google Drive (un solo token por proveedor) |

---

## Notas

- Las 6 tablas son del **módulo D**. Las tablas referenciadas (`ventas`, `usuarios`) pertenecen a otros módulos.
- `config_notificaciones` es **fila única** (id=1), similar a `configuracion_negocio` de Module A.
- `boletas_clientes` tiene `venta_id UNIQUE` porque una venta solo genera una boleta.
- `boletas_clientes` incluye `cliente_nombre` (VARCHAR 120) para identificar al cliente. Default: "Cliente 1".
- `notificaciones` no tiene borrado lógico; se purgan después de 30 días (RNF-14).
- `respaldos` expiran después de 30 días; los scripts de limpieza los eliminan.
- `oauth_tokens` almacena tokens OAuth para Google Drive. Un solo registro por proveedor (google_drive). El `refresh_token` nunca expira; el `access_token` se renueva automáticamente.
