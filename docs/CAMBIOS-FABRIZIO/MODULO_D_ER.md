# Diagrama Entidad-Relación — Módulo D (Documentos)

**Módulo**: Notas de Venta, Reportes, Notificaciones, Respaldos e Infraestructura
**Base de datos**: PostgreSQL 16
**Zona horaria**: America/Lima

---

## Diagrama Mermaid

```mermaid
erDiagram
    notificaciones {
        BIGINT id PK
        VARCHAR(30) tipo "STOCK_BAJO | APERTURA_CAJA | CIERRE_CAJA | SOLICITUD_INGRESO | SISTEMA"
        VARCHAR(120) titulo "titulo de la notificacion"
        TEXT mensaje "cuerpo del mensaje"
        BOOLEAN leida "DEFAULT FALSE"
        VARCHAR(60) entidad_origen "nullable — tabla origen"
        VARCHAR(60) entidad_id "nullable — ID de la entidad origen"
        BIGINT usuario_id FK "nullable → usuarios.id (NULL = broadcast admin)"
        BIGINT producto_id FK "nullable → productos.id (Module B)"
        TIMESTAMPTZ created_at "DEFAULT NOW()"
    }

    config_notificaciones {
        INT id PK "siempre 1 (fila unica)"
        VARCHAR(20) nivel_detalle "BAJO | MEDIO | ALTO"
        TIMESTAMPTZ updated_at "DEFAULT NOW()"
    }

    respaldos {
        BIGINT id PK
        VARCHAR(255) archivo_nombre "ej: tienda_sistema_20260725_230707.sql"
        BIGINT tamano_bytes "tamano del archivo"
        VARCHAR(20) estado "PENDIENTE | COMPLETADO | FALLIDO"
        TIMESTAMPTZ generado_en "DEFAULT NOW()"
        TIMESTAMPTZ expira_en "DEFAULT now() + 21 dias"
        BIGINT usuario_id FK "nullable → usuarios.id (NULL si automatico)"
        VARCHAR(255) drive_file_id "nullable — ID en Google Drive"
    }

    oauth_tokens {
        BIGINT id PK
        VARCHAR(50) proveedor "google_drive"
        TEXT access_token "token temporal (expira en 1 hora)"
        TEXT refresh_token "token para renovar (nunca expira)"
        TIMESTAMPTZ token_expiry "cuando expira el access_token"
        BIGINT usuario_id FK "nullable → usuarios.id (Module A)"
        TIMESTAMPTZ fecha_creacion "DEFAULT NOW()"
        TIMESTAMPTZ fecha_actualizacion "DEFAULT NOW()"
    }

    %% Relaciones externas (fuera de Module D)
    usuarios ||--o| notificaciones : "puede recibir"
    usuarios ||--o| oauth_tokens : "autoriza Drive"
    usuarios ||--o| respaldos : "crea respaldos manuales"
    productos ||--o| notificaciones : "puede generar alerta"
```

---

## Tablas resumen

| Tabla | PK | FK | Descripcion |
|-------|----|----|-------------|
| `notificaciones` | `id` (BIGINT) | `usuario_id` → `usuarios.id`, `producto_id` → `productos.id` | Notificaciones del sistema (stock bajo, caja, solicitudes, etc.) |
| `config_notificaciones` | `id` (INT, siempre 1) | — | Configuracion global de notificaciones |
| `respaldos` | `id` (BIGINT) | `usuario_id` → `usuarios.id` | Registro de copias de seguridad (Google Drive) |
| `oauth_tokens` | `id` (BIGINT) | `usuario_id` → `usuarios.id` | Tokens OAuth para Google Drive |

---

## Cardinalidades

| Relacion | Tipo | Descripcion |
|----------|------|-------------|
| `usuarios` → `notificaciones` | 1:0..N | Un usuario puede recibir muchas notificaciones (NULL = broadcast admin) |
| `usuarios` → `oauth_tokens` | 1:0..1 | Un usuario autoriza Google Drive (un solo token por proveedor) |
| `usuarios` → `respaldos` | 1:0..N | Un usuario puede crear muchos respaldos manuales |
| `productos` → `notificaciones` | 1:0..N | Un producto puede generar alertas de stock bajo |

---

## Notas

- Las 4 tablas son del **modulo D**. Las tablas referenciadas (`usuarios`, `productos`) pertenecen a otros modulos.
- `config_notificaciones` es **fila unica** (id=1), similar a `configuracion_negocio` de Module A.
- `notificaciones` no tiene borrado logico; se purgan despues de 30 dias (RNF-14).
- `respaldos` almacena archivos `.sql` en Google Drive (carpeta `respaldos/YYYY/MM/`). Retencion: 21 dias. `usuario_id` es NULL para respaldos automaticos (cada domingo).
- `oauth_tokens` almacena tokens OAuth para Google Drive. Un solo registro por proveedor (google_drive). El `refresh_token` nunca expira; el `access_token` se renueva automaticamente.
- Las tablas `boletas_clientes` y `archivos_drive` fueron eliminadas en migraciones anteriores.
