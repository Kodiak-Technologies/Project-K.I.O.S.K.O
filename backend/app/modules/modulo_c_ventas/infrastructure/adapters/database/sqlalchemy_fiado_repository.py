# Adaptador: implementa FiadoRepositoryPort usando SQLAlchemy.
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import Abono, Cliente, Fiado
from app.modules.modulo_c_ventas.domain.ports.fiado_repository_port import FiadoRepositoryPort
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import (
    AbonoModel,
    ClienteModel,
    FiadoModel,
)


def _cliente_a_entidad(fila: ClienteModel) -> Cliente:
    return Cliente(
        id=fila.id, nombre=fila.nombre, alias=fila.alias, telefono=fila.telefono,
        limite_credito=fila.limite_credito, activo=fila.activo, created_at=fila.created_at,
    )


def _fiado_a_entidad(fila: FiadoModel, cliente_nombre: str = "") -> Fiado:
    return Fiado(
        id=fila.id, venta_id=fila.venta_id, cliente_id=fila.cliente_id,
        monto_total=fila.monto_total, saldo_pendiente=fila.saldo_pendiente,
        estado=fila.estado, cliente_nombre=cliente_nombre, created_at=fila.created_at,
    )


def _abono_a_entidad(fila: AbonoModel) -> Abono:
    return Abono(
        id=fila.id, fiado_id=fila.fiado_id, turno_id=fila.turno_id,
        usuario_id=fila.usuario_id, registrado_por=fila.registrado_por,
        codigo_metodo=fila.codigo_metodo, es_efectivo=fila.es_efectivo,
        monto=fila.monto, metodo_pago_id=fila.metodo_pago_id, created_at=fila.created_at,
    )


class SqlAlchemyFiadoRepository(FiadoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    # ---- Clientes ----
    async def listar_clientes(self, busqueda: str | None = None) -> list[Cliente]:
        consulta = select(ClienteModel).where(ClienteModel.activo.is_(True)).order_by(ClienteModel.nombre)
        if busqueda:
            patron = f"%{busqueda.strip()}%"
            consulta = consulta.where(
                or_(ClienteModel.nombre.ilike(patron), ClienteModel.alias.ilike(patron))
            )
        filas = (await self._db.execute(consulta)).scalars()
        return [_cliente_a_entidad(f) for f in filas]

    async def buscar_cliente(self, cliente_id: int) -> Cliente | None:
        fila = (
            await self._db.execute(select(ClienteModel).where(ClienteModel.id == cliente_id))
        ).scalar_one_or_none()
        return _cliente_a_entidad(fila) if fila else None

    async def crear_cliente(self, cliente: Cliente) -> Cliente:
        fila = ClienteModel(
            nombre=cliente.nombre, alias=cliente.alias, telefono=cliente.telefono,
            limite_credito=cliente.limite_credito, activo=cliente.activo,
        )
        self._db.add(fila)
        await self._db.flush()
        return _cliente_a_entidad(fila)

    async def actualizar_cliente(self, cliente_id: int, cambios: dict) -> Cliente:
        editables = ("nombre", "alias", "telefono", "limite_credito", "activo")
        valores = {k: v for k, v in cambios.items() if k in editables}
        if valores:
            await self._db.execute(
                update(ClienteModel).where(ClienteModel.id == cliente_id).values(**valores)
            )
        fila = (
            await self._db.execute(select(ClienteModel).where(ClienteModel.id == cliente_id))
        ).scalar_one()
        return _cliente_a_entidad(fila)

    # ---- Fiados ----
    async def crear_fiado(self, fiado: Fiado) -> Fiado:
        fila = FiadoModel(
            venta_id=fiado.venta_id, cliente_id=fiado.cliente_id,
            monto_total=fiado.monto_total, saldo_pendiente=fiado.saldo_pendiente,
            estado=fiado.estado,
        )
        self._db.add(fila)
        await self._db.flush()
        fiado.id = fila.id
        fiado.created_at = fila.created_at
        return fiado

    async def buscar_fiado(self, fiado_id: int) -> Fiado | None:
        fila = (
            await self._db.execute(
                select(FiadoModel, ClienteModel.nombre)
                .join(ClienteModel, FiadoModel.cliente_id == ClienteModel.id)
                .where(FiadoModel.id == fiado_id)
            )
        ).first()
        return _fiado_a_entidad(fila[0], fila[1]) if fila else None

    async def listar_fiados(
        self, cliente_id: int | None = None, solo_pendientes: bool = True
    ) -> list[Fiado]:
        consulta = (
            select(FiadoModel, ClienteModel.nombre)
            .join(ClienteModel, FiadoModel.cliente_id == ClienteModel.id)
            .order_by(FiadoModel.id.desc())
        )
        if cliente_id is not None:
            consulta = consulta.where(FiadoModel.cliente_id == cliente_id)
        if solo_pendientes:
            consulta = consulta.where(FiadoModel.estado == "PENDIENTE")
        filas = (await self._db.execute(consulta)).all()
        return [_fiado_a_entidad(f, nombre) for f, nombre in filas]

    async def deuda_de_cliente(self, cliente_id: int) -> Decimal:
        total = (
            await self._db.execute(
                select(func.coalesce(func.sum(FiadoModel.saldo_pendiente), 0)).where(
                    FiadoModel.cliente_id == cliente_id, FiadoModel.estado == "PENDIENTE"
                )
            )
        ).scalar()
        return Decimal(str(total))

    async def actualizar_saldo(self, fiado_id: int, nuevo_saldo: Decimal, estado: str) -> None:
        await self._db.execute(
            update(FiadoModel)
            .where(FiadoModel.id == fiado_id)
            .values(saldo_pendiente=nuevo_saldo, estado=estado)
        )

    # ---- Abonos ----
    async def crear_abono(self, abono: Abono) -> Abono:
        fila = AbonoModel(
            fiado_id=abono.fiado_id, turno_id=abono.turno_id, usuario_id=abono.usuario_id,
            registrado_por=abono.registrado_por, metodo_pago_id=abono.metodo_pago_id,
            codigo_metodo=abono.codigo_metodo, es_efectivo=abono.es_efectivo, monto=abono.monto,
        )
        self._db.add(fila)
        await self._db.flush()
        abono.id = fila.id
        abono.created_at = fila.created_at
        return abono

    async def abonos_de_fiado(self, fiado_id: int) -> list[Abono]:
        filas = (
            await self._db.execute(
                select(AbonoModel).where(AbonoModel.fiado_id == fiado_id).order_by(AbonoModel.id)
            )
        ).scalars()
        return [_abono_a_entidad(f) for f in filas]

    async def abonos_de_turno(self, turno_id: int) -> list[dict]:
        filas = (
            await self._db.execute(
                select(AbonoModel, ClienteModel.nombre)
                .join(FiadoModel, AbonoModel.fiado_id == FiadoModel.id)
                .join(ClienteModel, FiadoModel.cliente_id == ClienteModel.id)
                .where(AbonoModel.turno_id == turno_id)
                .order_by(AbonoModel.id.desc())
            )
        ).all()
        return [
            {
                "id": abono.id,
                "fiado_id": abono.fiado_id,
                "cliente": nombre,
                "metodo": abono.codigo_metodo,
                "monto": float(abono.monto),
                "registrado_por": abono.registrado_por,
                "created_at": abono.created_at.isoformat() if abono.created_at else None,
            }
            for abono, nombre in filas
        ]
