# Engine SQLAlchemy async compartido, SessionLocal y get_db(). Sin lógica de negocio.
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.config.settings import settings


def _preparar_url_y_connect_args(
    url: str,
) -> tuple[str, dict]:
    """Limpia la URL y extrae los kwargs validos para asyncpg.connect().

    asyncpg solo acepta unos pocos kwargs en connect(): host, port, user,
    password, database, statement_cache_size, etc. Parametros como
    `connection_limit` o `pool_timeout` son de SQLAlchemy/psycopg2: si quedan
    en la URL, SQLAlchemy los reenvia a asyncpg.connect() y revientan con
    `TypeError: connect() got an unexpected keyword argument ...`.

    Esta funcion extrae los params que asyncpg soporta como connect_args y
    ELIMINA el resto de la URL (se replican via `pool_size` en create_async_engine
    en lugar de como query param).
    """
    ASYNCPG_ARGS = {"statement_cache_size"}
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    connect_args: dict = {}
    for k, v in params.items():
        if k in ASYNCPG_ARGS:
            value = v[0] if len(v) == 1 else v
            # asyncpg exige tipos concretos: statement_cache_size es int.
            if k == "statement_cache_size":
                value = int(value)
            connect_args[k] = value
    safe_url = urlunparse(parsed._replace(query=""))
    return safe_url, connect_args


_url_limpia, _connect_args = _preparar_url_y_connect_args(settings.database_url)

# pool_pre_ping=True: descarta conexiones muertas antes de usarlas.
# pool_recycle=300: recicla conexiones cada 5 min, evitando que Supabase
#   Pooler (pgbouncer en modo transaction) las cierre silenciosamente.
# pool_size=2: replica el connection_limit=2 que estaba en la URL.
engine = create_async_engine(
    _url_limpia,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=2,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: una sesión por request, con commit/rollback automático."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
