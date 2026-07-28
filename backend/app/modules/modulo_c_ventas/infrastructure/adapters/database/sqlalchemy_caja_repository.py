# Adaptador: implementa CajaRepositoryPort usando SQLAlchemy.
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import ArqueoCaja, TurnoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import TURNO_ABIERTO, TURNO_CERRADO
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import (
    ArqueoCajaModel,
    TurnoCajaModel,
)


def _a_entidad(fila: TurnoCajaModel) -> TurnoCaja:
    return TurnoCaja(
        id=fila.id,
        usuario_id=fila.usuario_id,
        abierto_por=fila.abierto_por,
        monto_inicial=fila.monto_inicial,
        estado=fila.estado,
        abierto_en=fila.abierto_en,
        cerrado_en=fila.cerrado_en,
        monto_final=fila.monto_final,
        usuario_cierre_id=fila.usuario_cierre_id,
        cerrado_por=fila.cerrado_por,
        asignado_a_id=fila.asignado_a_id,
    )


class SqlAlchemyCajaRepository(CajaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def turno_abierto(self) -> TurnoCaja | None:
        fila = (
            await self._db.execute(
                select(TurnoCajaModel).where(TurnoCajaModel.estado == TURNO_ABIERTO)
            )
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def buscar_por_id(self, turno_id: int) -> TurnoCaja | None:
        fila = (
            await self._db.execute(select(TurnoCajaModel).where(TurnoCajaModel.id == turno_id))
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def abrir(self, turno: TurnoCaja) -> TurnoCaja:
        fila = TurnoCajaModel(
            usuario_id=turno.usuario_id,
            abierto_por=turno.abierto_por,
            monto_inicial=turno.monto_inicial,
            estado=turno.estado,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def actualizar(self, turno: TurnoCaja) -> TurnoCaja:
        fila = (
            await self._db.execute(select(TurnoCajaModel).where(TurnoCajaModel.id == turno.id))
        ).scalar_one()
        fila.asignado_a_id = turno.asignado_a_id
        fila.monto_inicial = turno.monto_inicial
        await self._db.flush()
        return _a_entidad(fila)

    async def listar(self, limite: int = 30) -> list[TurnoCaja]:
        filas = (
            await self._db.execute(
                select(TurnoCajaModel).order_by(TurnoCajaModel.id.desc()).limit(limite)
            )
        ).scalars()
        return [_a_entidad(f) for f in filas]

    async def cerrar(
        self,
        turno_id: int,
        monto_final: Decimal,
        usuario_cierre_id: int | None,
        cerrado_por: str,
    ) -> TurnoCaja:
        fila = (
            await self._db.execute(select(TurnoCajaModel).where(TurnoCajaModel.id == turno_id))
        ).scalar_one()
        fila.estado = TURNO_CERRADO
        fila.monto_final = monto_final
        fila.cerrado_en = datetime.now(timezone.utc)
        fila.usuario_cierre_id = usuario_cierre_id
        fila.cerrado_por = cerrado_por
        await self._db.flush()
        return _a_entidad(fila)

    async def guardar_arqueo(self, arqueo: ArqueoCaja) -> ArqueoCaja:
        fila = ArqueoCajaModel(
            turno_id=arqueo.turno_id,
            usuario_id=arqueo.usuario_id,
            cerrado_por=arqueo.cerrado_por,
            efectivo_esperado=arqueo.efectivo_esperado,
            efectivo_contado=arqueo.efectivo_contado,
            diferencia=arqueo.diferencia,
            comentario=arqueo.comentario,
            total_vendido=arqueo.total_vendido,
            totales_por_metodo=arqueo.totales_por_metodo,
        )
        self._db.add(fila)
        await self._db.flush()
        arqueo.id = fila.id
        arqueo.created_at = fila.created_at
        return arqueo

    async def arqueos_por_turno(self, turno_ids: list[int]) -> dict[int, ArqueoCaja]:
        if not turno_ids:
            return {}
        filas = (
            await self._db.execute(
                select(ArqueoCajaModel).where(ArqueoCajaModel.turno_id.in_(turno_ids))
            )
        ).scalars()
        return {
            f.turno_id: ArqueoCaja(
                id=f.id,
                turno_id=f.turno_id,
                usuario_id=f.usuario_id,
                cerrado_por=f.cerrado_por,
                efectivo_esperado=f.efectivo_esperado,
                efectivo_contado=f.efectivo_contado,
                diferencia=f.diferencia,
                comentario=f.comentario,
                total_vendido=f.total_vendido,
                totales_por_metodo=f.totales_por_metodo,
                created_at=f.created_at,
            )
            for f in filas
        }

    async def totales_de_turno(self, turno_id: int) -> dict:
        # Modelo entrada/salida de efectivo del TURNO:
        #  + entra al vender (aunque la venta se anule después, el reverso registra
        #    su propia salida en el turno en que ocurre — HU-C08)
        #  - sale con devoluciones/anulaciones hechas durante este turno
        por_metodo = (
            await self._db.execute(
                text(
                    "SELECT pv.codigo_metodo, pv.es_efectivo, SUM(pv.monto) AS monto "
                    "FROM pagos_venta pv JOIN ventas v ON v.id = pv.venta_id "
                    "WHERE v.turno_id = :turno_id "
                    "GROUP BY pv.codigo_metodo, pv.es_efectivo"
                ),
                {"turno_id": turno_id},
            )
        ).all()
        totales_por_metodo = {fila.codigo_metodo: float(fila.monto) for fila in por_metodo}
        ventas_efectivo = sum(
            (fila.monto for fila in por_metodo if fila.es_efectivo), Decimal("0")
        )

        resumen_ventas = (
            await self._db.execute(
                text(
                    "SELECT COALESCE(SUM(total), 0) AS total, COUNT(*) AS numero "
                    "FROM ventas WHERE turno_id = :turno_id"
                ),
                {"turno_id": turno_id},
            )
        ).one()

        # Reversos (HU-C08) del turno; la tabla se crea en su propia migración,
        # por eso se consulta solo si ya existe.
        devoluciones_efectivo = await self._suma_si_existe(
            "SELECT COALESCE(SUM(efectivo_devuelto), 0) FROM anulaciones "
            "WHERE turno_id = :turno_id",
            turno_id,
            "anulaciones",
        )

        return {
            "ventas_efectivo": ventas_efectivo,
            "totales_por_metodo": totales_por_metodo,
            "total_vendido": resumen_ventas.total,
            "numero_ventas": resumen_ventas.numero,
            "devoluciones_efectivo": devoluciones_efectivo,
        }

    async def _suma_si_existe(self, sql: str, turno_id: int, tabla: str) -> Decimal:
        existe = (
            await self._db.execute(text("SELECT to_regclass(:tabla)"), {"tabla": tabla})
        ).scalar()
        if existe is None:
            return Decimal("0")
        valor = (await self._db.execute(text(sql), {"turno_id": turno_id})).scalar()
        return valor if valor is not None else Decimal("0")
