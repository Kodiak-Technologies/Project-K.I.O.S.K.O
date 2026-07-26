# Engine SQLAlchemy async compartido, SessionLocal y get_db(). Sin lógica de negocio.
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.config.settings import settings

# El pooler de Supabase (Supavisor) se usa en **transaction mode** (puerto
# 6543): la conexión al servidor se devuelve al terminar cada transacción en
# vez de quedar tomada toda la sesión. En session mode (5432) el tope era de 15
# clientes y un solo uvicorn podía agotarlo él solo, porque el pool por defecto
# de SQLAlchemy es 5 + 10 de overflow = 15.
#
# Transaction mode tiene una contra: asyncpg cachea prepared statements POR
# conexión, y como entre transacciones te puede tocar otra conexión física,
# fallan intermitentemente con "prepared statement _asyncpg_stmt_N_ does not
# exist". Por eso se desactivan los dos cachés (el de asyncpg y el del dialecto
# de SQLAlchemy). El costo es replanificar cada consulta; con este volumen no
# se nota.
#
# Requisitos que el código ya cumple para poder usar transaction mode:
#   - los advisory locks son `pg_advisory_xact_lock` (por transacción, no de
#     sesión): ver `sqlalchemy_producto_repository.siguiente_correlativo_interno`;
#   - no hay `SET` de sesión, tablas temporales, LISTEN/NOTIFY ni cursores
#     server-side, que no sobreviven al cambio de conexión.
engine = create_async_engine(
    settings.database_url,
    # Tope duro: sin overflow el proceso nunca abre más de 5 conexiones.
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    # El pooler corta conexiones inactivas y en Windows asyncpg no siempre lo
    # detecta (falla con AttributeError en el transporte SSL, que el pre_ping
    # no reconoce como desconexión). Renovar cada 4 min las descarta antes de
    # que mueran y evita los 500 intermitentes tras un rato sin uso.
    pool_recycle=240,
    connect_args={
        # Sin caché de prepared statements: ni el de asyncpg ni el del
        # dialecto. Un statement cacheado en una conexión no existe en la
        # siguiente que te toque.
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        # Y por si algo igual prepara: nombres únicos. Por defecto asyncpg los
        # numera (`_asyncpg_stmt_1_`) y detrás de un pooler dos conexiones
        # distintas pueden pelearse el mismo nombre.
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
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
