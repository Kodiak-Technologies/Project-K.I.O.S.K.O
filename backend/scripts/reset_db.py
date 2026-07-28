# Reset de datos para desarrollo: vacía bitácora, sesiones, usuarios, rol_permisos
# y configuración, y vuelve a correr el seed para dejar el baseline limpio.
# roles y permisos no se tocan (el seed los reutiliza).
#
# TRUNCATE no dispara el trigger de fila trg_bitacora_inmutable, así que la
# inmutabilidad de la bitácora sigue protegida frente a la app; este script es la
# única puerta de borrado y por eso se niega a correr fuera de un entorno local.
#
# Uso:  python -m scripts.reset_db
import asyncio
import sys

from sqlalchemy import text

from app.shared.config.settings import settings
from app.shared.database.session import engine
from scripts.seed import seed

TABLAS = ["bitacora_auditoria", "sesiones", "usuarios", "rol_permisos", "configuracion_negocio"]


async def reset() -> None:
    if settings.environment != "local":
        print(f"ERROR: entorno '{settings.environment}' — este script solo corre en 'local'.")
        sys.exit(1)

    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {', '.join(TABLAS)} RESTART IDENTITY CASCADE"))
    print(f"Tablas vaciadas: {', '.join(TABLAS)}")

    # seed() hace engine.dispose() al final, así que no hace falta repetirlo acá.
    await seed()


if __name__ == "__main__":
    asyncio.run(reset())
