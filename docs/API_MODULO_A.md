# API del Módulo A + Guía de integración para los módulos B, C y D

Base URL local: `http://localhost:8000` · Swagger interactivo: `/docs`
Autenticación: header `Authorization: Bearer <access_token>` (excepto login/refresh).

## 1. Contrato de endpoints

### Autenticación (`/auth`)

| Método | Ruta | Body | Respuesta OK | Errores |
|---|---|---|---|---|
| POST | `/auth/login` | `{username, password}` | 200 `{access_token, refresh_token, token_type, usuario}` | 401 credenciales (mensaje genérico), 423 cuenta bloqueada |
| POST | `/auth/refresh` | `{refresh_token}` | 200 igual que login (tokens **rotados**) | 401 sesión inválida/expirada |
| POST | `/auth/logout` | `{refresh_token}` | 204 | 401 sin token |
| GET | `/auth/me` | — | 200 `usuario` | 401 |
| PATCH | `/auth/password` | `{password_actual, password_nueva}` | 204 | 401 actual incorrecta, 422 política |

Forma de `usuario`: `{id, username, nombre, rol_id, rol, activo, debe_cambiar_password, ultimo_acceso, created_at}`.

### Usuarios (`/usuarios`) — requiere permiso `usuarios.gestionar` (solo ADMIN)

| Método | Ruta | Body | Respuesta OK | Errores |
|---|---|---|---|---|
| GET | `/usuarios` | — | 200 `usuario[]` (excluye eliminados) | 401/403 |
| POST | `/usuarios` | `{username, nombre, password, rol_id, forzar_cambio_password}` | 201 `usuario` | 409 duplicado, 422 política |
| GET | `/usuarios/{id}` | — | 200 `usuario` | 404 |
| PATCH | `/usuarios/{id}` | `{nombre?, rol_id?}` | 200 `usuario` | 404 |
| DELETE | `/usuarios/{id}` | `{motivo?}` opcional | 204 (borrado **lógico**) | 404, 422 auto-eliminación |
| PATCH | `/usuarios/{id}/estado` | `{activo}` | 200 `usuario` (revoca sesiones al desactivar) | 404, 422 auto-desactivación |
| PATCH | `/usuarios/{id}/password` | `{password_nueva, forzar_cambio}` | 204 (revoca sesiones) | 404, 422 política |

### Roles y permisos — requiere `usuarios.gestionar`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/roles` | Lista roles (ADMIN=1, CAJERO=2 según seed) |
| GET | `/permisos` | Catálogo completo de permisos |
| GET | `/roles/{id}/permisos` | Permisos actuales del rol |
| PUT | `/roles/{id}/permisos` | Reemplaza permisos: `{permisos: ["codigo", ...]}` — aplica sin redeploy |

### Bitácora (`/bitacora`) — requiere `bitacora.ver` (solo ADMIN, **solo lectura**)

`GET /bitacora?desde=&hasta=&usuario_id=&accion=&entidad=&pagina=1&tamano_pagina=25`
→ 200 `{registros: [...], total, pagina, tamano_pagina}` (más recientes primero).
No existen PUT/PATCH/DELETE: la bitácora es inmutable (además reforzado con trigger en BD).

### Configuración (`/configuracion`)

| Método | Ruta | Quién | Descripción |
|---|---|---|---|
| GET | `/configuracion` | cualquier autenticado | Nombre, logo, colores, tipografía, TTLs, límites — **los módulos B/C/D leen de aquí** el nombre/logo para boletas y correos |
| PATCH | `/configuracion` | permiso `configuracion.editar` | Edición parcial de cualquier campo |
| POST | `/configuracion/logo` | permiso `configuracion.editar` | `multipart/form-data`, campo `archivo` (PNG/JPEG/WebP/SVG ≤ 500 KB) |

### Errores (todos los endpoints)

Formato: `{"detail": "mensaje en español"}` con códigos 401 (sin sesión/credenciales), 403 (sin permiso), 404 (no existe), 409 (conflicto), 422 (validación), 423 (cuenta bloqueada).

---

## 2. Guía de integración para Brayan (B), Clever (C) y Fabrizio (D)

El Módulo A expone su **contrato público** en un único archivo:
`app/modules/modulo_a_seguridad/infrastructure/dependencies.py`. Importen **solo de ahí** (regla de `docs/ARQUITECTURA.md` §4: nada de importar casos de uso o repos internos de otro módulo).

### 2.1 Proteger un endpoint (autenticación)

```python
from fastapi import APIRouter, Depends
from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user
from app.modules.modulo_a_seguridad.domain.entities import Usuario

router = APIRouter(prefix="/productos")

@router.get("")
async def listar_productos(usuario: Usuario = Depends(get_current_user)):
    # `usuario` es el usuario REAL desde BD (garantizado activo y no eliminado).
    ...
```

### 2.2 Exigir un permiso (RBAC — así el 403 lo valida el SERVIDOR)

```python
from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_permission

@router.post("/ingresos/{id}/aprobar")
async def aprobar_ingreso(
    id: int,
    usuario: Usuario = Depends(require_permission("inventario.aprobar_ingreso")),
):
    ...
```

Permisos disponibles: ver tabla `permisos` (seed) o `GET /permisos`. Si necesitan un permiso nuevo,
agréguenlo en `backend/scripts/seed.py` y avisen a Matías.

### 2.3 Registrar en la bitácora (¡háganlo en TODA operación relevante!)

```python
from fastapi import Request
from app.modules.modulo_a_seguridad.infrastructure.dependencies import contexto_request, get_auditoria

@router.post("/ventas")
async def registrar_venta(
    datos: ..., request: Request,
    usuario: Usuario = Depends(require_permission("ventas.registrar")),
    auditoria = Depends(get_auditoria),
):
    venta = ...  # su lógica
    ip, user_agent = contexto_request(request)
    await auditoria.ejecutar(
        accion="venta_registrada", entidad="ventas", entidad_id=venta.id,
        usuario_id=usuario.id, rol=usuario.rol_nombre,
        valor_nuevo={"total": str(venta.total), "items": venta.cantidad_items},
        ip=ip, user_agent=user_agent,
    )
```

Convención de `accion`: `<entidad>_<verbo_en_pasado>` (ej. `venta_anulada`, `precio_editado`, `ingreso_aprobado`).
Para cambios, llenen `valor_anterior` y `valor_nuevo`: la dueña quiere ver el antes/después.

### 2.4 Borrado lógico (obligatorio: NADA se borra físicamente)

```python
from app.shared.kernel.soft_delete import SoftDeleteMixin, marcar_borrado

class ProductoModel(Base, SoftDeleteMixin):  # agrega deleted_at / deleted_by
    __tablename__ = "productos"
    ...

# al "eliminar":
marcar_borrado(producto, usuario.id)   # + registrar en bitácora con accion="producto_eliminado"
# y en sus consultas normales:
select(ProductoModel).where(ProductoModel.deleted_at.is_(None))
```

### 2.5 Leer la configuración del negocio (logo/nombre para boletas, correos)

Vía HTTP interno (opción recomendada en `ARQUITECTURA.md` §4): `GET /configuracion` con el token del usuario,
o directamente el puerto público si están dentro del mismo proceso: `SqlAlchemyConfiguracionRepository(db).obtener()`
**solo** si lo consumen a través de `dependencies.py` (pidan a Matías exponerlo si lo necesitan seguido).
