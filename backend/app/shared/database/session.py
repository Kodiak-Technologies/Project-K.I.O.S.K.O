# Engine SQLAlchemy async compartido, SessionLocal y get_db(). Sin lógica de negocio.
from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.config.settings import settings

# El pooler de Supabase (Supavisor) tiene dos modos y cada uno pide una
# configuración distinta. Se detecta por el puerto de DATABASE_URL:
#
# - **Transaction mode** (puerto 6543): la conexión al servidor se devuelve al
#   terminar cada transacción. asyncpg cachea prepared statements POR conexión
#   y entre transacciones te puede tocar otra conexión física, así que fallan
#   intermitentemente con "prepared statement _asyncpg_stmt_N_ does not exist".
#   Por eso se desactivan los dos cachés (el de asyncpg y el del dialecto de
#   SQLAlchemy). El costo: cada consulta se prepara y se ejecuta = 2 viajes.
# - **Session mode** (5432, o Postgres directo/local): la conexión es nuestra
#   toda la sesión, el caché funciona y cada consulta repetida es 1 viaje. El
#   tope del pooler es de 15 clientes en total; con pool_size=5 y sin overflow
#   cada instancia ocupa como máximo 5 (por eso en Cloud Run va con
#   --max-instances acotado).
#
# Requisitos que el código ya cumple para poder usar transaction mode:
#   - los advisory locks son `pg_advisory_xact_lock` (por transacción, no de
#     sesión): ver `sqlalchemy_producto_repository.siguiente_correlativo_interno`;
#   - no hay `SET` de sesión, tablas temporales, LISTEN/NOTIFY ni cursores
#     server-side, que no sobreviven al cambio de conexión.
MODO_TRANSACCION = make_url(settings.database_url).port == 6543

_connect_args = (
    {
        # Sin caché de prepared statements: ni el de asyncpg ni el del
        # dialecto. Un statement cacheado en una conexión no existe en la
        # siguiente que te toque.
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        # Y por si algo igual prepara: nombres únicos. Por defecto asyncpg los
        # numera (`_asyncpg_stmt_1_`) y detrás de un pooler dos conexiones
        # distintas pueden pelearse el mismo nombre.
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }
    if MODO_TRANSACCION
    else {}  # session mode: cachés por defecto de asyncpg y del dialecto
)

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
