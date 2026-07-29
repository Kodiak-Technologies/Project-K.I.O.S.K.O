# Seed inicial: lo MÍNIMO para que el sistema arranque y se pueda operar.
#
# Qué siembra y por qué cada cosa es imprescindible:
#   - roles + permisos + rol_permisos → sin esto nadie puede hacer nada.
#   - un usuario ADMIN               → sin esto no hay forma de entrar.
#   - configuracion_negocio          → el backend responde 404 si falta la fila.
#   - config_notificaciones          → ídem para la pantalla de notificaciones.
#   - metodos_pago                   → sin esto NO SE PUEDE COBRAR: al registrar
#     una venta se valida el código contra esta tabla y, si no está, se rechaza.
#
# Lo que NO siembra, a propósito: productos, categorías, proveedores, ingresos
# ni ventas. Eso son datos del negocio, se cargan desde la aplicación. Para
# datos de ejemplo está `scripts.seed_demo`.
#
# Idempotente: se puede correr varias veces sin duplicar datos.
#
# Uso:  ADMIN_USERNAME=admin ADMIN_PASSWORD=... python -m scripts.seed
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
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import (
    MetodoPagoModel,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import (
    ConfigNotificacionesModel,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from app.shared.database.session import SessionLocal, engine

ROLES = [
    ("ADMIN", "Dueña de la tienda: control total del sistema."),
    ("CAJERO", "Vendedor: permisos limitados a la operación diaria."),
]

# (codigo, nombre, es_efectivo)
#
# EFECTIVO es obligatorio: `es_efectivo=True` es lo que hace que el monto cuente
# para el arqueo de caja (RF-17). Los demás son los que se usan de mostrador.
#
# Vale la pena editarlos acá antes de arrancar: hoy no hay pantalla para dar de
# alta un método de pago, así que lo que no esté en esta lista no se va a poder
# cobrar (existe `POST /metodos-pago`, pero ninguna pantalla lo usa todavía).
METODOS_PAGO = [
    ("EFECTIVO", "Efectivo", True),
    ("YAPE", "Yape", False),
    ("PLIN", "Plin", False),
    ("TARJETA", "Tarjeta", False),
    ("TRANSFERENCIA", "Transferencia", False),
]

# (codigo, descripcion, lo tiene CAJERO?)  — ADMIN los tiene todos.
PERMISOS = [
    ("usuarios.gestionar", "Crear, editar y desactivar usuarios", False),
    ("productos.crear", "Crear productos en el catálogo", False),
    ("productos.editar", "Editar productos del catálogo", False),
    ("categorias.gestionar", "Crear y editar categorías del catálogo", False),
    ("precios.editar", "Modificar precios", False),
    ("historial_precios.ver", "Consultar el historial de cambios de precio", False),
    # Ajuste manual de stock desde el catálogo: solo ADMIN (el cajero mueve
    # stock por solicitudes de ingreso y por ventas, nunca a mano).
    ("inventario.ajustar_stock", "Ajustar el stock a mano desde el catálogo", False),
    # El cajero necesita subir la foto de la boleta para poder enviar la solicitud (HU-B06).
    ("storage.upload", "Subir archivos (fotos de boleta y de producto)", True),
    ("inventario.aprobar_ingreso", "Aprobar ingresos de mercadería", False),
    ("inventario.solicitar_ingreso", "Solicitar/registrar ingresos de mercadería", True),
    ("inventario.ver", "Consultar inventario y stock", True),
    ("proveedores.compras_credito", "Registrar compras a crédito de proveedores", False),
    ("proveedores.gestionar", "Gestionar proveedores", False),
    ("proveedores.pagos", "Registrar pagos a proveedores", False),
    ("proveedores.ver", "Ver proveedores", True),
    ("ventas.registrar", "Registrar ventas en el POS", True),
    # El cajero puede anular/devolver dejando rastro (HU-C08); el ADMIN supervisa
    # desde el panel de caja y puede quitarle el permiso sin redeploy si lo desea.
    ("ventas.anular", "Anular ventas", True),
    ("ventas.devolver", "Registrar devoluciones de venta", True),
    ("metodos_pago.gestionar", "Agregar/desactivar métodos de pago", False),
    ("caja.abrir_turno", "Abrir turno de caja", True),
    ("caja.cerrar_turno", "Cerrar turno de caja", True),
    ("reportes.ver", "Ver reportes", False),
    ("registros.eliminar", "Borrado lógico de registros", False),
    ("bitacora.ver", "Consultar la bitácora de auditoría", False),
    ("configuracion.editar", "Editar configuración e identidad visual", False),
]


async def seed() -> None:
    # `pepe/pepe` es una comodidad para desarrollo local. Fuera de local hay que
    # pasar ADMIN_USERNAME/ADMIN_PASSWORD por entorno: son las credenciales del
    # único usuario que puede entrar al sistema recién instalado.
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
    if not admin_password:
        print("ERROR: ADMIN_PASSWORD está definida pero vacía.")
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

        # --- Configuración de notificaciones (fila única) ---
        config_notif = (
            await db.execute(select(ConfigNotificacionesModel).where(ConfigNotificacionesModel.id == 1))
        ).scalar_one_or_none()
        if config_notif is None:
            db.add(ConfigNotificacionesModel(id=1))

        # --- Métodos de pago ---
        # Sin al menos uno, el POS no puede cerrar una venta: `RegistrarVentaUseCase`
        # compara el código contra los métodos activos y rechaza lo que no esté.
        for codigo, nombre, es_efectivo in METODOS_PAGO:
            metodo = (
                await db.execute(select(MetodoPagoModel).where(MetodoPagoModel.codigo == codigo))
            ).scalar_one_or_none()
            if metodo is None:
                db.add(
                    MetodoPagoModel(
                        codigo=codigo, nombre=nombre, es_efectivo=es_efectivo, activo=True
                    )
                )

        await db.commit()
        print(
            f"Seed completado: {len(ROLES)} roles, {len(PERMISOS)} permisos, "
            f"{len(METODOS_PAGO)} métodos de pago, usuario '{admin_username}', "
            "configuración del negocio y de notificaciones."
        )

    # Cierra el pool antes de que asyncio.run() cierre el loop; si no, en Windows
    # las conexiones SSL se destruyen con el loop ya cerrado ("Event loop is closed").
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
