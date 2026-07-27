"""Conexiones asyncpg directas (sin SQLAlchemy), compatibles con el pooler.

Algunas tareas necesitan hablar con Postgres sin el ORM: el respaldo vuelca las
tablas fila por fila y el script de esquema ejecuta un .sql entero.

Esas conexiones NO pasan por el engine de `session.py`, así que no heredan su
configuración — y con el pooler en **transaction mode** (puerto 6543) eso
rompe: asyncpg cachea prepared statements por conexión y, como entre
transacciones te puede tocar otra conexión física, fallan con

    prepared statement "__asyncpg_stmt_81__" does not exist

Usá siempre `conectar()` en vez de `asyncpg.connect()` directo.
"""

import asyncpg


def opciones_pooler() -> dict:
    """kwargs de asyncpg necesarios detrás de un pooler en transaction mode.

    Sólo `statement_cache_size`: sin caché, un statement preparado en una
    conexión no puede faltar en la siguiente que devuelva el pooler.

    (El engine de `session.py` además pasa `prepared_statement_name_func` para
    generar nombres únicos, pero ese argumento lo consume el dialecto de
    SQLAlchemy: `asyncpg.connect()` no lo acepta.)
    """
    return {"statement_cache_size": 0}


async def conectar(dsn: str | None = None, **kwargs) -> asyncpg.Connection:
    """`asyncpg.connect` con las opciones del pooler ya aplicadas."""
    if dsn is not None:
        return await asyncpg.connect(dsn, **opciones_pooler(), **kwargs)
    return await asyncpg.connect(**opciones_pooler(), **kwargs)
