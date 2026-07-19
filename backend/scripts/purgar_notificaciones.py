import asyncio
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func

from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import NotificacionModel
from app.shared.database.session import SessionLocal, engine


async def purgar_notificaciones(dias: int = 30) -> int:
    limite = datetime.now(timezone.utc) - timedelta(days=dias)

    async with SessionLocal() as db:
        resultado = await db.execute(
            delete(NotificacionModel).where(NotificacionModel.created_at < limite)
        )
        await db.commit()
        return resultado.rowcount


async def main() -> None:
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    eliminadas = await purgar_notificaciones(dias)
    print(f"Notificaciones eliminadas (>{dias} días): {eliminadas}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
