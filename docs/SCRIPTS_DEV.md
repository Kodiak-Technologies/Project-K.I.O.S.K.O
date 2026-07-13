# Scripts de desarrollo del backend

Utilidades para trabajar con la base de datos en local. Ambos se corren desde `backend/` con el venv activado (o con `.venv\Scripts\python.exe` directo).

## `python -m scripts.seed`

Crea el baseline del sistema y es **idempotente** (correrlo dos veces no duplica nada):

- Roles `ADMIN` y `CAJERO`.
- Los 15 permisos y su asignación a cada rol.
- El usuario administrador inicial. Usuario y contraseña salen de las variables de entorno `ADMIN_USERNAME` / `ADMIN_PASSWORD` (con default de desarrollo si no están definidas — revisa `scripts/seed.py`; en producción SIEMPRE definir las variables).
- La fila única de `configuracion_negocio`.

Detalle técnico: al final hace `await engine.dispose()`. Sin eso, en Windows `asyncio.run()` cierra el event loop con conexiones SSL del pool aún vivas y el script termina con un traceback feo (`RuntimeError: Event loop is closed`) aunque el seed haya funcionado. Si escribes otro script async que use el engine, copia ese patrón.

## `python -m scripts.reset_db`

Borra los **datos de prueba** y deja la base limpia en un paso:

1. `TRUNCATE ... RESTART IDENTITY CASCADE` sobre `bitacora_auditoria`, `sesiones`, `usuarios`, `rol_permisos` y `configuracion_negocio` (los IDs vuelven a 1). `roles` y `permisos` no se tocan.
2. Vuelve a correr el seed.

Protecciones:

- **Se niega a correr si `ENVIRONMENT` no es `local`** — nunca lo apuntes a producción.
- La bitácora es inmutable vía trigger (`trg_bitacora_inmutable` bloquea `UPDATE`/`DELETE` fila por fila). Este script puede vaciarla igualmente porque `TRUNCATE` en PostgreSQL **no dispara triggers de fila** — el trigger sigue protegiendo a la aplicación, y este script es la única puerta de borrado, solo para desarrollo.
- `usuarios` no se puede borrar con `DELETE` normal mientras la bitácora lo referencie (`ON DELETE RESTRICT`); el `TRUNCATE` en bloque con `CASCADE` resuelve las dependencias entre las tablas listadas.

## Convención de usernames (afecta al login)

Los usernames son **siempre en minúsculas** (`^[a-z0-9_]{3,30}$`): el formulario de creación lo valida y el login del frontend normaliza con `toLowerCase()` antes de enviar. Si creas usuarios a mano (seed, SQL), respétalo — un username con mayúsculas en la BD sería imposible de loguear desde el frontend. La búsqueda en el backend es por igualdad exacta.

Otro recordatorio útil: tras N intentos fallidos (configurable, default 3) la cuenta se bloquea por M minutos (default 15). Si en desarrollo te bloqueas, `python -m scripts.reset_db` también lo resuelve.
