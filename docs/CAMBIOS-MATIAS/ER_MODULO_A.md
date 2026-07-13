# Diagrama Entidad-Relación — Módulo A (Seguridad, Accesos, Configuración y Auditoría)

Tablas del Módulo A en PostgreSQL. Todas las fechas son `TIMESTAMPTZ`. Nada se borra físicamente:
`usuarios` usa borrado lógico (`deleted_at`/`deleted_by`) y `bitacora_auditoria` es inmutable (trigger + REVOKE).

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : "clasifica (1 rol - N usuarios)"
    ROLES ||--o{ ROL_PERMISOS : "tiene"
    PERMISOS ||--o{ ROL_PERMISOS : "se asigna en"
    USUARIOS ||--o{ SESIONES : "abre (1 usuario - N sesiones)"
    USUARIOS ||--o{ BITACORA_AUDITORIA : "genera (1 usuario - N eventos)"
    USUARIOS ||--o{ CONFIGURACION_NEGOCIO : "actualiza (updated_by)"

    ROLES {
        int id PK
        varchar nombre UK "ADMIN | CAJERO"
        varchar descripcion
    }

    PERMISOS {
        int id PK
        varchar codigo UK "ej. ventas.anular"
        varchar descripcion
    }

    ROL_PERMISOS {
        int rol_id PK, FK "-> roles.id (RESTRICT)"
        int permiso_id PK, FK "-> permisos.id (RESTRICT)"
    }

    USUARIOS {
        bigint id PK
        varchar username UK "indice; alias tipo vendedor1"
        varchar nombre "nombre para mostrar"
        varchar password_hash "bcrypt cost 12"
        int rol_id FK "-> roles.id (RESTRICT)"
        boolean activo
        boolean debe_cambiar_password
        int intentos_fallidos
        timestamptz bloqueado_hasta "bloqueo temporal"
        timestamptz ultimo_acceso
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at "borrado LOGICO"
        bigint deleted_by
    }

    SESIONES {
        bigint id PK
        bigint usuario_id FK "-> usuarios.id (RESTRICT)"
        varchar refresh_token_hash UK "SHA-256, nunca el token en claro"
        varchar ip
        varchar user_agent
        timestamptz expira_en "TTL segun rol, configurable"
        boolean revocada
        timestamptz created_at
    }

    BITACORA_AUDITORIA {
        bigint id PK
        bigint usuario_id FK "-> usuarios.id (RESTRICT), null si login de user inexistente"
        varchar rol
        varchar accion "indice implicito via consultas; ej. login_fallido"
        varchar entidad "indice; ej. usuarios, ventas"
        varchar entidad_id
        jsonb valor_anterior
        jsonb valor_nuevo
        text motivo
        varchar ip
        varchar user_agent
        timestamptz created_at "indice"
    }

    CONFIGURACION_NEGOCIO {
        int id PK "fila unica, id = 1"
        varchar nombre_negocio
        text logo_url "URL o data-URI base64"
        varchar color_primario
        varchar color_secundario
        varchar tipografia
        int session_ttl_admin_minutos "default 43200 (30 dias)"
        int session_ttl_cajero_minutos "default 720 (12 horas)"
        int max_intentos_login "default 3"
        int minutos_bloqueo "default 15"
        bigint updated_by FK "-> usuarios.id (RESTRICT)"
        timestamptz updated_at
    }
```

## Decisiones de diseño

- **FK con `ON DELETE RESTRICT`** en todo lo que apunta a `usuarios`: un usuario con historial no puede desaparecer de la BD — garantiza la trazabilidad que pide la dueña.
- **`rol_permisos` en BD** (no permisos hardcodeados): el ADMIN puede ajustar permisos sin redeploy (`PUT /roles/{id}/permisos`).
- **`sesiones.refresh_token_hash`**: se guarda solo el SHA-256 del refresh token; si la BD se filtra, los tokens no sirven.
- **`bitacora_auditoria` inmutable**: trigger `trg_bitacora_inmutable` lanza excepción ante `UPDATE`/`DELETE`, y el usuario de aplicación además tiene revocados esos privilegios (defensa en dos capas).
- **JSONB para valor_anterior/valor_nuevo**: permite auditar el "antes y después" de cualquier entidad de cualquier módulo sin cambiar el schema.
