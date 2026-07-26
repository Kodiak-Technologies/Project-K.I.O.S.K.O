# Crea el esquema completo ejecutando `db/schema.sql` sobre DATABASE_URL.
#
# `db/schema.sql` es la única fuente de verdad del esquema y reemplaza a los
# cuatro `schema_modulo_*.sql` que había antes, que se habían desincronizado
# entre sí y con el código.
#
# OJO: el script asume una base VACÍA — crea tablas, no las parchea. Para
# recrear desde cero hay que borrar el esquema primero (ver `--reset`).
#
# Uso:  python -m scripts.aplicar_schema           (sobre una base vacía)
#       python -m scripts.aplicar_schema --reset   (BORRA TODO y recrea)
#
# La alternativa equivalente es `alembic upgrade head`: la migración inicial
# ejecuta este mismo archivo.
import asyncio
import sys
from pathlib import Path

import asyncpg

from app.shared.config.settings import settings

ESQUEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


async def aplicar(reset: bool = False) -> None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conexion = await asyncpg.connect(dsn)
    try:
        if reset:
            await conexion.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            print("Esquema public borrado y recreado.")

        existentes = await conexion.fetchval(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
        )
        if existentes and not reset:
            print(
                f"ABORTADO: la base ya tiene {existentes} tablas.\n"
                "Este script crea el esquema desde cero. Usá --reset para "
                "borrarlas (se pierde TODO) o apuntá a una base vacía."
            )
            return

        # Sin argumentos, asyncpg usa el protocolo simple: permite scripts con
        # múltiples sentencias y bloques $$ ... $$.
        await conexion.execute(ESQUEMA.read_text(encoding="utf-8"))
        tablas = await conexion.fetchval(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
        )
        print(f"OK: esquema creado ({tablas} tablas) con su seed inicial.")
        print("Usuario inicial: admin / admin123 (pide cambio de contraseña).")
    finally:
        await conexion.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(aplicar(reset="--reset" in sys.argv))
