# Seed inicial: roles, permisos, usuario ADMIN y fila única de configuración.
# Idempotente: se puede correr varias veces sin duplicar datos.
#
# Uso:  ADMIN_USERNAME=admin ADMIN_PASSWORD=... python -m scripts.seed
# La contraseña del ADMIN viene SIEMPRE de la variable de entorno, nunca hardcodeada.
import asyncio
import os
import sys

from sqlalchemy import select

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    ConfiguracionNegocioModel,
    PermisoModel,
    RolModel,
    RolPermisoModel,
    UsuarioModel,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from app.shared.database.session import SessionLocal, engine

ROLES = [
    ("ADMIN", "Dueña de la tienda: control total del sistema."),
    ("CAJERO", "Vendedor: permisos limitados a la operación diaria."),
]

# (codigo, descripcion, lo tiene CAJERO?)  — ADMIN los tiene todos.
PERMISOS = [
    ("usuarios.gestionar", "Crear, editar y desactivar usuarios", False),
    ("productos.crear", "Crear productos en el catálogo", False),
    ("productos.editar", "Editar productos del catálogo", False),
    ("precios.editar", "Modificar precios", False),
    ("inventario.aprobar_ingreso", "Aprobar ingresos de mercadería", False),
    ("inventario.solicitar_ingreso", "Solicitar/registrar ingresos de mercadería", True),
    ("inventario.ver", "Consultar inventario y stock", True),
    ("ventas.registrar", "Registrar ventas en el POS", True),
    # El cajero puede anular/devolver dejando rastro (HU-C08); el ADMIN supervisa
    # desde el panel de caja y puede quitarle el permiso sin redeploy si lo desea.
    ("ventas.anular", "Anular ventas", True),
    ("ventas.devolver", "Registrar devoluciones de venta", True),
    ("metodos_pago.gestionar", "Agregar/desactivar métodos de pago", False),
    ("clientes.gestionar", "Registrar y editar clientes del fiado", True),
    ("clientes.limite_credito", "Fijar límite de crédito por cliente", False),
    ("fiados.abonar", "Registrar abonos de fiados", True),
    ("caja.abrir_turno", "Abrir turno de caja", True),
    ("caja.cerrar_turno", "Cerrar turno de caja", True),
    ("reportes.ver", "Ver reportes", False),
    ("registros.eliminar", "Borrado lógico de registros", False),
    ("bitacora.ver", "Consultar la bitácora de auditoría", False),
    ("configuracion.editar", "Editar configuración e identidad visual", False),
]


async def seed() -> None:
    admin_username = os.environ.get("ADMIN_USERNAME", "pepe")
    admin_password = os.environ.get("ADMIN_PASSWORD", "pepe")
    if not admin_password:
        print("ERROR: define la variable de entorno ADMIN_PASSWORD (nunca va en el código).")
        sys.exit(1)

    async with SessionLocal() as db:
        # --- Roles ---
        roles: dict[str, RolModel] = {}
        for nombre, descripcion in ROLES:
            rol = (await db.execute(select(RolModel).where(RolModel.nombre == nombre))).scalar_one_or_none()
            if rol is None:
                rol = RolModel(nombre=nombre, descripcion=descripcion)
                db.add(rol)
                await db.flush()
            roles[nombre] = rol

        # --- Permisos ---
        permisos: dict[str, PermisoModel] = {}
        for codigo, descripcion, _ in PERMISOS:
            permiso = (
                await db.execute(select(PermisoModel).where(PermisoModel.codigo == codigo))
            ).scalar_one_or_none()
            if permiso is None:
                permiso = PermisoModel(codigo=codigo, descripcion=descripcion)
                db.add(permiso)
                await db.flush()
            permisos[codigo] = permiso

        # --- Asignación rol-permiso ---
        async def asignar(rol: RolModel, codigo: str) -> None:
            existe = (
                await db.execute(
                    select(RolPermisoModel).where(
                        RolPermisoModel.rol_id == rol.id,
                        RolPermisoModel.permiso_id == permisos[codigo].id,
                    )
                )
            ).scalar_one_or_none()
            if existe is None:
                db.add(RolPermisoModel(rol_id=rol.id, permiso_id=permisos[codigo].id))

        for codigo, _, es_de_cajero in PERMISOS:
            await asignar(roles["ADMIN"], codigo)
            if es_de_cajero:
                await asignar(roles["CAJERO"], codigo)

        # --- Usuario ADMIN inicial ---
        admin = (
            await db.execute(select(UsuarioModel).where(UsuarioModel.username == admin_username))
        ).scalar_one_or_none()
        if admin is None:
            db.add(
                UsuarioModel(
                    username=admin_username,
                    nombre="Administradora",
                    password_hash=BcryptPasswordHasher().hashear(admin_password),
                    rol_id=roles["ADMIN"].id,
                    activo=True,
                )
            )

        # --- Configuración (fila única) ---
        config = (
            await db.execute(select(ConfiguracionNegocioModel).where(ConfiguracionNegocioModel.id == 1))
        ).scalar_one_or_none()
        if config is None:
            db.add(ConfiguracionNegocioModel(id=1))

        await db.commit()
        print(f"Seed completado: roles, {len(PERMISOS)} permisos, usuario '{admin_username}' y configuración.")

    # Cierra el pool antes de que asyncio.run() cierre el loop; si no, en Windows
    # las conexiones SSL se destruyen con el loop ya cerrado ("Event loop is closed").
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
