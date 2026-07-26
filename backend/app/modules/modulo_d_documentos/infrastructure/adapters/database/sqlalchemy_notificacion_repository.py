from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.domain.entities import Notificacion
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import NotificacionModel


def _a_entidad(fila: NotificacionModel) -> Notificacion:
    return Notificacion(
        id=fila.id,
        tipo=fila.tipo,
        titulo=fila.titulo,
        mensaje=fila.mensaje,
        leida=fila.leida,
        entidad_origen=fila.entidad_origen,
        entidad_id=fila.entidad_id,
        usuario_id=fila.usuario_id,
        producto_id=fila.producto_id,
        created_at=fila.created_at,
    )


class SqlAlchemyNotificacionRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def listar(self) -> list[Notificacion]:
        resultado = await self._db.execute(
            select(NotificacionModel)
            .order_by(NotificacionModel.leida.asc(), NotificacionModel.created_at.desc())
        )
        return [_a_entidad(fila) for fila in resultado.scalars().all()]

    async def listar_por_usuario(
        self,
        usuario_id: int,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[Notificacion], int]:
        """(notificaciones, total). Con `page`/`page_size` acota en SQL: la
        bandeja crece sin techo y antes se traía entera en cada consulta."""
        condicion = (NotificacionModel.usuario_id == usuario_id) | (
            NotificacionModel.usuario_id.is_(None)
        )
        total = (
            await self._db.execute(
                select(func.count()).select_from(NotificacionModel).where(condicion)
            )
        ).scalar_one()
        consulta = (
            select(NotificacionModel)
            .where(condicion)
            # Desempate por PK: sin él la paginación de la bandeja no es
            # determinista cuando dos avisos comparten `created_at`.
            .order_by(
                NotificacionModel.leida.asc(),
                NotificacionModel.created_at.desc(),
                NotificacionModel.id.desc(),
            )
        )
        if page is not None and page_size is not None:
            consulta = consulta.offset((page - 1) * page_size).limit(page_size)
        resultado = await self._db.execute(consulta)
        return [_a_entidad(fila) for fila in resultado.scalars().all()], total

    async def marcar_leida(self, notificacion_id: int) -> Notificacion | None:
        fila = await self._db.get(NotificacionModel, notificacion_id)
        if fila is None:
            return None
        fila.leida = True
        await self._db.flush()
        return _a_entidad(fila)

    async def marcar_todas_leidas(self, usuario_id: int) -> int:
        resultado = await self._db.execute(
            update(NotificacionModel)
            .where(
                (NotificacionModel.usuario_id == usuario_id)
                | (NotificacionModel.usuario_id.is_(None)),
                NotificacionModel.leida == False,
            )
            .values(leida=True)
        )
        return resultado.rowcount

    async def crear(self, notificacion: Notificacion) -> Notificacion:
        fila = NotificacionModel(
            tipo=notificacion.tipo,
            titulo=notificacion.titulo,
            mensaje=notificacion.mensaje,
            entidad_origen=notificacion.entidad_origen,
            entidad_id=notificacion.entidad_id,
            usuario_id=notificacion.usuario_id,
            producto_id=notificacion.producto_id,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def eliminar_expiradas(self, dias: int = 30) -> int:
        limite = datetime.now(timezone.utc) - timedelta(days=dias)
        resultado = await self._db.execute(
            delete(NotificacionModel).where(NotificacionModel.created_at < limite)
        )
        return resultado.rowcount
