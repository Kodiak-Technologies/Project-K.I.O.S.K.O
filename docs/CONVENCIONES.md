# Convenciones del equipo

## 1. Ramas por módulo

Cada quien trabaja en ramas prefijadas con su módulo:

```
modulo-a/<descripcion-corta>     # Matías   — ej: modulo-a/login-jwt
modulo-b/<descripcion-corta>     # Brayan   — ej: modulo-b/aprobacion-ingresos
modulo-c/<descripcion-corta>     # Clever   — ej: modulo-c/apertura-caja
modulo-d/<descripcion-corta>     # Fabrizio — ej: modulo-d/subida-boletas-drive
```

- `main` siempre debe quedar en estado desplegable.
- Los cambios a `main` entran por Pull Request, revisados idealmente por al menos otro de los 4 (aunque sea rápido).
- Si tu cambio toca `app/shared/` o `src/shared/` (lo verdaderamente transversal), avisa al resto antes de mergear — ahí sí se pisan los 4 módulos.

## 2. Nombres de archivos y carpetas (backend)

- Python: `snake_case.py` para archivos y funciones, `PascalCase` para clases.
- Un archivo de caso de uso = un verbo + su propósito: `crear_usuario_usecase.py`, `aprobar_ingreso_usecase.py`.
- Los puertos siempre terminan en `_port.py` y las clases en `Port` (`UsuarioRepositoryPort`).
- Los adaptadores describen la tecnología concreta que usan: `sqlalchemy_usuario_repository.py`, `bcrypt_password_hasher.py`, `jwt_token_service.py`.
- Los routers terminan en `_router.py` (`auth_router.py`, `ventas_router.py`).

## 3. Nombres de archivos y carpetas (frontend)

- Componentes y páginas: `PascalCase.tsx` (`GestionUsuarios.tsx`).
- Hooks: `camelCase.ts` empezando con `use` (`useAuth.ts`).
- Puertos y adaptadores de servicio: `<recurso>.port.ts` y `<recurso>.http-adapter.ts` (`auth.port.ts`, `auth.http-adapter.ts`).
- Tipos/DTOs: `camelCase.ts` o `PascalCase.ts` según si exportan principalmente tipos (`Usuario.ts`) o utilidades.

## 4. Commits

Formato: `modulo-x: mensaje corto en imperativo`.

Ejemplos:
```
modulo-a: agregar validacion de contrasena en creacion de usuario
modulo-b: implementar flujo de aprobacion de ingresos
modulo-c: registrar anulacion de ventas en caja
modulo-d: subir boletas generadas a Google Drive
shared: actualizar manejo global de errores HTTP
```

Para cambios que no son de un módulo específico (configuración raíz, CI, docs), usa el prefijo `shared:` o `docs:`.

## 5. Pull Requests

- Título: mismo formato que el commit principal (`modulo-b: aprobacion de ingresos`).
- Descripción breve: qué hace, por qué, y si toca algo de `shared/` o de otro módulo (y por qué, ver regla de comunicación entre módulos en `ARQUITECTURA.md` §4).
- Evita mezclar cambios de dos módulos distintos en el mismo PR.
