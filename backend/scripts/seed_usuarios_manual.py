# Usuarios de demo para generar las capturas del manual de usuario.
#
# Crea `manual_admin` (ADMIN) y `manual_cajero` (CAJERO) con una contraseña
# conocida y `debe_cambiar_password=False`, para poder entrar directo sin que el
# sistema interrumpa con el cambio de clave obligatorio.
#
# No toca los usuarios reales. Idempotente: si ya existen, no hace nada.
#
# Uso:      python -m scripts.seed_usuarios_manual
# Deshacer: python -m scripts.seed_usuarios_manual --borrar
import asyncio
import sys

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    RolModel,
    SesionModel,
    UsuarioModel,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from app.shared.database.session import SessionLocal, engine

PASSWORD = "Manual2026"

USUARIOS = [
    ("manual_admin", "Ana Torres (demo manual)", "ADMIN"),
    ("manual_cajero", "Luis Ramos (demo manual)", "CAJERO"),
]


async def _borrar(db) -> None:
    nombres = [u for u, _, _ in USUARIOS]
    ids = (
        (
            await db.execute(
                select(UsuarioModel.id).where(UsuarioModel.username.in_(nombres))
            )
        )
        .scalars()
        .all()
    )
    if not ids:
        print("No hay usuarios de demo que borrar.")
        return
    # Las sesiones referencian al usuario con ON DELETE RESTRICT: van primero.
    await db.execute(delete(SesionModel).where(SesionModel.usuario_id.in_(ids)))
    try:
        await db.execute(delete(UsuarioModel).where(UsuarioModel.id.in_(ids)))
        await db.commit()
        print(f"Borrados {len(ids)} usuarios de demo.")
    except IntegrityError:
        # Esperado en cuanto el usuario entró al sistema una vez: la bitácora lo
        # referencia con ON DELETE RESTRICT y el histórico no se borra. La baja
        # lógica es la salida correcta, no forzar el DELETE.
        await db.rollback()
        await db.execute(
            update(UsuarioModel).where(UsuarioModel.id.in_(ids)).values(activo=False)
        )
        await db.commit()
        print(
            f"Desactivados {len(ids)} usuarios de demo (no se pueden borrar: ya\n"
            "tienen registros en la bitácora y el histórico no se elimina)."
        )
    print("Los proveedores y productos creados NO se tocan.")


async def sembrar(borrar: bool = False) -> None:
    async with SessionLocal() as db:
        if borrar:
            await _borrar(db)
            await engine.dispose()
            return

        roles = {
            r.nombre: r
            for r in (await db.execute(select(RolModel))).scalars().all()
        }
        faltantes = [rol for _, _, rol in USUARIOS if rol not in roles]
        if faltantes:
            print(f"ABORTADO: faltan los roles {faltantes}. Corre `python -m scripts.seed`.")
            await engine.dispose()
            return

        hasher = BcryptPasswordHasher()
        creados = 0
        for username, nombre, rol in USUARIOS:
            existe = (
                await db.execute(
                    select(UsuarioModel).where(UsuarioModel.username == username)
                )
            ).scalar_one_or_none()
            if existe is not None:
                continue
            db.add(
                UsuarioModel(
                    username=username,
                    nombre=nombre,
                    password_hash=hasher.hashear(PASSWORD),
                    rol_id=roles[rol].id,
                    activo=True,
                    # Sin esto el primer login exige cambiar la clave y corta el
                    # recorrido de las capturas.
                    debe_cambiar_password=False,
                )
            )
            creados += 1

        await db.commit()
        if creados:
            print(f"Usuarios creados: {creados}")
        else:
            print("Los usuarios de demo ya existían.")
        for username, _, rol in USUARIOS:
            print(f"  {username:<15} {rol:<7} contraseña: {PASSWORD}")
        print()
        print("Para borrarlos: python -m scripts.seed_usuarios_manual --borrar")

    await engine.dispose()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sembrar(borrar="--borrar" in sys.argv))
