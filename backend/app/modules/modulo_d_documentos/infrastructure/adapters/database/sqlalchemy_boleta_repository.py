from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.domain.entities import Boleta
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import BoletaModel


def _a_entidad(fila: BoletaModel) -> Boleta:
    return Boleta(
        id=fila.id,
        venta_id=fila.venta_id,
        numero=fila.numero,
        total=float(fila.total),
        emitida_en=fila.emitida_en,
        url_pdf=fila.url_pdf,
    )


class SqlAlchemyBoletaRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def buscar_por_id(self, boleta_id: int) -> Boleta | None:
        resultado = await self._db.execute(
            select(BoletaModel).where(BoletaModel.id == boleta_id)
        )
        fila = resultado.scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def buscar_por_venta_id(self, venta_id: int) -> Boleta | None:
        resultado = await self._db.execute(
            select(BoletaModel).where(BoletaModel.venta_id == venta_id)
        )
        fila = resultado.scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def listar(
        self, desde: str | None = None, hasta: str | None = None, q: str | None = None
    ) -> list[Boleta]:
        consulta = select(BoletaModel).order_by(BoletaModel.emitida_en.desc())

        if desde:
            consulta = consulta.where(BoletaModel.emitida_en >= desde)
        if hasta:
            consulta = consulta.where(BoletaModel.emitida_en <= hasta)
        if q:
            consulta = consulta.where(BoletaModel.numero.ilike(f"%{q}%"))

        resultado = await self._db.execute(consulta)
        return [_a_entidad(fila) for fila in resultado.scalars().all()]

    async def crear(self, boleta: Boleta) -> Boleta:
        fila = BoletaModel(
            venta_id=boleta.venta_id,
            numero=boleta.numero,
            total=boleta.total,
            url_pdf=boleta.url_pdf,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def generar_siguiente_numero(self) -> str:
        resultado = await self._db.execute(
            select(func.count(BoletaModel.id))
        )
        total = resultado.scalar() or 0
        siguiente = total + 1
        return f"B001-{siguiente:06d}"
