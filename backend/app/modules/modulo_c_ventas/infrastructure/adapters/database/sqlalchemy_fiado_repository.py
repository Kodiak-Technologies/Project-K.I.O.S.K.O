# Adaptador: implementa FiadoRepositoryPort con SQL directo (tablas de esquema_fiados.py).
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import ClienteFiado, MovimientoFiado
from app.modules.modulo_c_ventas.domain.ports.fiado_repository_port import FiadoRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import MOV_FIADO_CONSUMO
from app.shared.config.zona_horaria import zona_negocio

_COLUMNAS_CLIENTE = (
    "c.id, c.nombre, c.telefono, c.nota, c.limite_mensual, c.saldo, c.activo, c.created_at, "
    "COALESCE(m.consumo, 0) AS consumo_mes"
)
# Lo fiado en el mes calendario (zona del negocio), neto de anulaciones/devoluciones.
_CONSUMO_MES = (
    "LEFT JOIN ("
    "  SELECT cliente_id, SUM(CASE WHEN tipo = 'CONSUMO' THEN monto "
    "                              WHEN tipo = 'REVERSO' THEN -monto ELSE 0 END) AS consumo "
    "  FROM movimientos_fiado WHERE created_at >= :inicio_mes GROUP BY cliente_id"
    ") m ON m.cliente_id = c.id"
)
_COLUMNAS_MOVIMIENTO = (
    "mf.id, mf.cliente_id, mf.tipo, mf.monto, mf.saldo_resultante, mf.usuario_id, "
    "mf.registrado_por, mf.venta_id, mf.anulacion_id, mf.turno_id, mf.codigo_metodo, "
    "mf.es_efectivo, mf.entra_a_caja, mf.nota, mf.created_at, c.nombre AS cliente_nombre"
)


def _inicio_mes() -> datetime:
    ahora = datetime.now(zona_negocio())
    return ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _cliente(fila) -> ClienteFiado:
    return ClienteFiado(
        id=fila.id, nombre=fila.nombre, telefono=fila.telefono, nota=fila.nota,
        limite_mensual=fila.limite_mensual, saldo=fila.saldo, activo=fila.activo,
        consumo_mes=Decimal(fila.consumo_mes), created_at=fila.created_at,
    )


def _movimiento(fila) -> MovimientoFiado:
    return MovimientoFiado(
        id=fila.id, cliente_id=fila.cliente_id, tipo=fila.tipo, monto=fila.monto,
        saldo_resultante=fila.saldo_resultante, usuario_id=fila.usuario_id,
        registrado_por=fila.registrado_por, venta_id=fila.venta_id,
        anulacion_id=fila.anulacion_id, turno_id=fila.turno_id,
        codigo_metodo=fila.codigo_metodo, es_efectivo=fila.es_efectivo,
        entra_a_caja=fila.entra_a_caja, nota=fila.nota,
        cliente_nombre=fila.cliente_nombre, created_at=fila.created_at,
    )


class SqlAlchemyFiadoRepository(FiadoRepositoryPort):
    # Se confirma una sola vez por proceso que las tablas existen: si el esquema
    # no se pudo crear, caja y movimientos del turno siguen funcionando sin fiados.
    _esquema_ok = False

    def __init__(self, db: AsyncSession):
        self._db = db

    async def hay_esquema(self) -> bool:
        if not SqlAlchemyFiadoRepository._esquema_ok:
            existe = (
                await self._db.execute(text("SELECT to_regclass('movimientos_fiado')"))
            ).scalar()
            SqlAlchemyFiadoRepository._esquema_ok = existe is not None
        return SqlAlchemyFiadoRepository._esquema_ok

    async def listar_clientes(
        self, buscar: str | None = None, incluir_inactivos: bool = False
    ) -> list[ClienteFiado]:
        condiciones, parametros = [], {"inicio_mes": _inicio_mes()}
        if not incluir_inactivos:
            condiciones.append("c.activo")
        if buscar and buscar.strip():
            condiciones.append("(c.nombre ILIKE :patron OR c.telefono ILIKE :patron)")
            parametros["patron"] = f"%{buscar.strip()}%"
        donde = f"WHERE {' AND '.join(condiciones)} " if condiciones else ""
        filas = await self._db.execute(
            text(
                f"SELECT {_COLUMNAS_CLIENTE} FROM clientes_fiado c {_CONSUMO_MES} {donde}"
                "ORDER BY c.saldo ASC, lower(c.nombre)"
            ),
            parametros,
        )
        return [_cliente(f) for f in filas]

    async def buscar_cliente(self, cliente_id: int) -> ClienteFiado | None:
        fila = (
            await self._db.execute(
                text(f"SELECT {_COLUMNAS_CLIENTE} FROM clientes_fiado c {_CONSUMO_MES} WHERE c.id = :id"),
                {"id": cliente_id, "inicio_mes": _inicio_mes()},
            )
        ).one_or_none()
        return _cliente(fila) if fila else None

    async def existe_nombre(self, nombre: str, excepto_id: int | None = None) -> bool:
        sql = "SELECT 1 FROM clientes_fiado WHERE lower(nombre) = lower(:nombre)"
        parametros: dict = {"nombre": nombre}
        if excepto_id is not None:
            sql += " AND id <> :id"
            parametros["id"] = excepto_id
        return (await self._db.execute(text(sql), parametros)).first() is not None

    async def crear_cliente(self, cliente: ClienteFiado, usuario_id: int) -> ClienteFiado:
        nuevo_id = (
            await self._db.execute(
                text(
                    "INSERT INTO clientes_fiado (nombre, telefono, nota, limite_mensual, creado_por) "
                    "VALUES (:nombre, :telefono, :nota, :limite, :usuario_id) RETURNING id"
                ),
                {
                    "nombre": cliente.nombre, "telefono": cliente.telefono, "nota": cliente.nota,
                    "limite": cliente.limite_mensual, "usuario_id": usuario_id,
                },
            )
        ).scalar_one()
        return await self.buscar_cliente(nuevo_id)

    async def actualizar_cliente(self, cliente_id: int, cambios: dict) -> ClienteFiado:
        permitidos = ("nombre", "telefono", "nota", "limite_mensual", "activo")
        sets = [f"{campo} = :{campo}" for campo in permitidos if campo in cambios]
        if sets:
            await self._db.execute(
                text(
                    f"UPDATE clientes_fiado SET {', '.join(sets)}, updated_at = now() WHERE id = :id"
                ),
                {"id": cliente_id, **{k: v for k, v in cambios.items() if k in permitidos}},
            )
        return await self.buscar_cliente(cliente_id)

    async def registrar_movimiento(
        self, movimiento: MovimientoFiado, delta_saldo: Decimal
    ) -> MovimientoFiado:
        # Una sentencia: el UPDATE del saldo y el asiento con el saldo resultante.
        # Si dos cajas mueven la misma cuenta a la vez, la fila queda bloqueada y
        # cada asiento ve el saldo correcto.
        fila = (
            await self._db.execute(
                text(
                    "WITH c AS ("
                    "  UPDATE clientes_fiado SET saldo = saldo + :delta, updated_at = now() "
                    "  WHERE id = :cliente_id RETURNING id, saldo"
                    ") "
                    "INSERT INTO movimientos_fiado (cliente_id, tipo, monto, saldo_resultante, "
                    "  venta_id, anulacion_id, turno_id, metodo_pago_id, codigo_metodo, "
                    "  es_efectivo, entra_a_caja, nota, usuario_id, registrado_por) "
                    "SELECT c.id, CAST(:tipo AS varchar), CAST(:monto AS numeric), c.saldo, "
                    "  CAST(:venta_id AS bigint), CAST(:anulacion_id AS bigint), "
                    "  CAST(:turno_id AS bigint), CAST(:metodo_pago_id AS integer), "
                    "  CAST(:codigo_metodo AS varchar), CAST(:es_efectivo AS boolean), "
                    "  CAST(:entra_a_caja AS boolean), CAST(:nota AS varchar), "
                    "  CAST(:usuario_id AS bigint), CAST(:registrado_por AS varchar) "
                    "FROM c RETURNING id, saldo_resultante, created_at"
                ),
                {
                    "delta": delta_saldo,
                    "cliente_id": movimiento.cliente_id,
                    "tipo": movimiento.tipo,
                    "monto": movimiento.monto,
                    "venta_id": movimiento.venta_id,
                    "anulacion_id": movimiento.anulacion_id,
                    "turno_id": movimiento.turno_id,
                    "metodo_pago_id": movimiento.metodo_pago_id,
                    "codigo_metodo": movimiento.codigo_metodo,
                    "es_efectivo": movimiento.es_efectivo,
                    "entra_a_caja": movimiento.entra_a_caja,
                    "nota": movimiento.nota,
                    "usuario_id": movimiento.usuario_id,
                    "registrado_por": movimiento.registrado_por,
                },
            )
        ).one()
        movimiento.id = fila.id
        movimiento.saldo_resultante = fila.saldo_resultante
        movimiento.created_at = fila.created_at
        return movimiento

    async def movimientos_de_cliente(self, cliente_id: int, limite: int = 200) -> list[MovimientoFiado]:
        filas = await self._db.execute(
            text(
                f"SELECT {_COLUMNAS_MOVIMIENTO} FROM movimientos_fiado mf "
                "JOIN clientes_fiado c ON c.id = mf.cliente_id "
                "WHERE mf.cliente_id = :id ORDER BY mf.created_at DESC, mf.id DESC LIMIT :limite"
            ),
            {"id": cliente_id, "limite": limite},
        )
        return [_movimiento(f) for f in filas]

    async def cobros_de_turno(self, turno_id: int) -> list[MovimientoFiado]:
        if not await self.hay_esquema():
            return []
        filas = await self._db.execute(
            text(
                f"SELECT {_COLUMNAS_MOVIMIENTO} FROM movimientos_fiado mf "
                "JOIN clientes_fiado c ON c.id = mf.cliente_id "
                "WHERE mf.turno_id = :turno_id AND mf.entra_a_caja "
                "ORDER BY mf.created_at, mf.id"
            ),
            {"turno_id": turno_id},
        )
        return [_movimiento(f) for f in filas]

    async def fiado_pendiente_de_venta(self, venta_id: int) -> tuple[int | None, Decimal]:
        if not await self.hay_esquema():
            return None, Decimal("0")
        fila = (
            await self._db.execute(
                text(
                    "SELECT cliente_id, SUM(CASE WHEN tipo = 'CONSUMO' THEN monto "
                    "                            WHEN tipo = 'REVERSO' THEN -monto ELSE 0 END) AS pendiente "
                    "FROM movimientos_fiado WHERE venta_id = :venta_id GROUP BY cliente_id"
                ),
                {"venta_id": venta_id},
            )
        ).first()
        if fila is None:
            return None, Decimal("0")
        return fila.cliente_id, max(Decimal(fila.pendiente), Decimal("0"))

    async def clientes_por_venta(self, venta_ids: list[int]) -> dict[int, str]:
        if not venta_ids or not await self.hay_esquema():
            return {}
        filas = await self._db.execute(
            text(
                "SELECT DISTINCT mf.venta_id, c.nombre FROM movimientos_fiado mf "
                "JOIN clientes_fiado c ON c.id = mf.cliente_id "
                "WHERE mf.venta_id = ANY(CAST(:ids AS bigint[])) AND mf.tipo = :consumo"
            ),
            {"ids": venta_ids, "consumo": MOV_FIADO_CONSUMO},
        )
        return {f.venta_id: f.nombre for f in filas}

    async def fiado_revertido_por_anulacion(self, anulacion_ids: list[int]) -> dict[int, Decimal]:
        if not anulacion_ids or not await self.hay_esquema():
            return {}
        filas = await self._db.execute(
            text(
                "SELECT anulacion_id, SUM(monto) AS monto FROM movimientos_fiado "
                "WHERE anulacion_id = ANY(CAST(:ids AS bigint[])) GROUP BY anulacion_id"
            ),
            {"ids": anulacion_ids},
        )
        return {f.anulacion_id: f.monto for f in filas}

    async def cobros_por_metodo_de_turno(self, turno_id: int) -> list:
        """[(codigo_metodo, es_efectivo, monto)] de lo que entró a la caja del turno."""
        if not await self.hay_esquema():
            return []
        return (
            await self._db.execute(
                text(
                    "SELECT codigo_metodo, es_efectivo, SUM(monto) AS monto FROM movimientos_fiado "
                    "WHERE turno_id = :turno_id AND entra_a_caja "
                    "GROUP BY codigo_metodo, es_efectivo"
                ),
                {"turno_id": turno_id},
            )
        ).all()
