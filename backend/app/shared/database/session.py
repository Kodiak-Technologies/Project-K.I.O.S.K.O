# Engine SQLAlchemy async compartido, SessionLocal y get_db(). Sin lógica de negocio.
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.config.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    # El pooler de Supabase corta conexiones inactivas y en Windows asyncpg no
    # siempre lo detecta (falla con AttributeError en el transporte SSL, que el
    # pre_ping no reconoce como desconexión). Renovar cada 4 min las descarta
    # antes de que mueran y evita los 500 intermitentes tras un rato sin uso.
    pool_recycle=240,
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
