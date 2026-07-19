# Aplica los scripts DDL de db/ directamente sobre DATABASE_URL.
#
# ¿Por qué no alembic? La BD compartida del equipo tiene aplicada una línea de
# migraciones de otra rama (módulo D) cuyos archivos no existen en esta rama, así
# que `alembic upgrade` no puede resolver la revisión actual. Los scripts de db/
# son idempotentes y NO tocan la tabla alembic_version.
#
# Uso:  python -m scripts.aplicar_schema            (aplica todos los schemas)
#       python -m scripts.aplicar_schema modulo_c   (solo los que contengan "modulo_c")
import asyncio
import sys
from pathlib import Path

import asyncpg

from app.shared.config.settings import settings

DIRECTORIO_DB = Path(__file__).resolve().parent.parent / "db"

# Orden explícito: productos (B) primero porque detalles_venta (C) le hace FK.
ARCHIVOS = [
    "schema_modulo_b_minimo.sql",
    "schema_modulo_c.sql",
]


async def aplicar(filtro: str | None = None) -> None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conexion = await asyncpg.connect(dsn)
    try:
        for nombre in ARCHIVOS:
            if filtro and filtro not in nombre:
                continue
            ruta = DIRECTORIO_DB / nombre
            if not ruta.exists():
                print(f"(omitido: {nombre} no existe todavía)")
                continue
            sql = ruta.read_text(encoding="utf-8")
            # Sin argumentos, asyncpg usa el protocolo simple: permite scripts
            # con múltiples sentencias y bloques DO $$ ... $$.
            await conexion.execute(sql)
            print(f"OK: {nombre}")
    finally:
        await conexion.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(aplicar(sys.argv[1] if len(sys.argv) > 1 else None))
