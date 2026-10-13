# Caso de uso: fiados (cuentas de clientes con crédito).
#
# Reglas acordadas con la dueña:
# - Fiar NO suma a la caja: la venta se registra con el método FIADO y se carga
#   a la cuenta del cliente (CONSUMO). Suma a la caja recién cuando paga (PAGO),
#   en el turno en que paga, con el método con que paga.
# - Una sola cuenta por cliente: el saldo es positivo si tiene crédito ya pagado
#   (ADELANTO, solo ADMIN, entra a la caja del turno) y negativo si debe. Lo fiado
#   gasta primero el saldo a favor; lo que falte queda como deuda.
# - El límite es MENSUAL, lo edita solo el ADMIN y NO bloquea: si un cliente lo
#   pasa se fía igual y queda una alerta para la administradora.
# - Pagar fiado lo puede hacer cualquiera; no puede pagarse más de lo que debe
#   (el excedente sería un adelanto, que es decisión del ADMIN).
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import ClienteFiado, MovimientoFiado
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.fiado_repository_port import FiadoRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.metodo_pago_repository_port import (
    MetodoPagoRepositoryPort,
)
from app.modules.modulo_c_ventas.domain.value_objects import (
    METODO_FIADO,
    MOV_FIADO_ADELANTO,
    MOV_FIADO_CONSUMO,
    MOV_FIADO_PAGO,
    MOV_FIADO_REVERSO,
    monto_dinero,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ProhibidoError,
    ValidacionError,
)

ROL_ADMIN = "ADMIN"


class GestionarFiadosUseCase:
    def __init__(
        self,
        repo: FiadoRepositoryPort,
        caja_repo: CajaRepositoryPort,
        metodos_repo: MetodoPagoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
        notificador=None,
    ):
        self._repo = repo
        self._caja = caja_repo
        self._metodos = metodos_repo
        self._auditoria = auditoria
        self._notificador = notificador

    # ------------------------------------------------------------------ consultas
    async def listar(self, buscar: str | None = None, incluir_inactivos: bool = False) -> list[ClienteFiado]:
        return await self._repo.listar_clientes(buscar, incluir_inactivos)

    async def obtener(self, cliente_id: int) -> ClienteFiado:
        cliente = await self._repo.buscar_cliente(cliente_id)
        if cliente is None:
            raise NoEncontradoError("Cliente no encontrado.")
        return cliente

    async def estado_de_cuenta(self, cliente_id: int) -> tuple[ClienteFiado, list[MovimientoFiado]]:
        cliente = await self.obtener(cliente_id)
        return cliente, await self._repo.movimientos_de_cliente(cliente_id)

    # ------------------------------------------------------------------ clientes
    async def crear_cliente(
        self, usuario_id: int, rol: str, nombre: str, telefono: str | None = None,
        nota: str | None = None, limite_mensual: Decimal | None = None,
        ip: str = "", user_agent: str = "",
    ) -> ClienteFiado:
        nombre = " ".join(nombre.split())
        if not nombre:
            raise ValidacionError("El nombre del cliente es obligatorio.")
        if await self._repo.existe_nombre(nombre):
            raise ConflictoError(f"Ya existe un cliente llamado '{nombre}'.")
        # Cualquiera registra al cliente; el límite solo lo asigna el ADMIN.
        limite = monto_dinero(limite_mensual or 0) if rol == ROL_ADMIN else Decimal("0")
        cliente = await self._repo.crear_cliente(
            ClienteFiado(
                id=None, nombre=nombre, telefono=(telefono or "").strip() or None,
                nota=(nota or "").strip() or None, limite_mensual=limite,
            ),
            usuario_id,
        )
        await self._auditoria.ejecutar(
            accion="cliente_fiado_creado", entidad="clientes_fiado", entidad_id=cliente.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={"nombre": cliente.nombre, "limite_mensual": float(limite)},
            ip=ip, user_agent=user_agent,
        )
        return cliente

    async def actualizar_cliente(
        self, usuario_id: int, rol: str, cliente_id: int, cambios: dict,
        ip: str = "", user_agent: str = "",
    ) -> ClienteFiado:
        actual = await self.obtener(cliente_id)
        if rol != ROL_ADMIN and ({"limite_mensual", "activo"} & cambios.keys()):
            raise ProhibidoError("Solo el administrador puede cambiar el límite o desactivar clientes.")
        limpios: dict = {}
        if "nombre" in cambios and cambios["nombre"] is not None:
            nombre = " ".join(cambios["nombre"].split())
            if not nombre:
                raise ValidacionError("El nombre del cliente es obligatorio.")
            if await self._repo.existe_nombre(nombre, excepto_id=cliente_id):
                raise ConflictoError(f"Ya existe un cliente llamado '{nombre}'.")
            limpios["nombre"] = nombre
        for campo in ("telefono", "nota"):
            if campo in cambios:
                limpios[campo] = (cambios[campo] or "").strip() or None
        if cambios.get("limite_mensual") is not None:
            limpios["limite_mensual"] = monto_dinero(cambios["limite_mensual"])
        if cambios.get("activo") is not None:
            limpios["activo"] = bool(cambios["activo"])
        actualizado = await self._repo.actualizar_cliente(cliente_id, limpios)
        await self._auditoria.ejecutar(
            accion="cliente_fiado_editado", entidad="clientes_fiado", entidad_id=cliente_id,
            usuario_id=usuario_id, rol=rol,
            valor_anterior={
                "nombre": actual.nombre, "limite_mensual": float(actual.limite_mensual),
                "activo": actual.activo,
            },
            valor_nuevo={k: (float(v) if isinstance(v, Decimal) else v) for k, v in limpios.items()},
            ip=ip, user_agent=user_agent,
        )
        return actualizado

    # ------------------------------------------------------------------ dinero que entra a caja
    async def registrar_pago(
        self, usuario_id: int, nombre_usuario: str, rol: str, cliente_id: int,
        monto, metodo: str, nota: str | None = None, ip: str = "", user_agent: str = "",
    ) -> MovimientoFiado:
        """El cliente paga (todo o parte) lo que debe: entra a la caja del turno ACTUAL."""
        cliente = await self.obtener(cliente_id)
        monto = monto_dinero(monto)
        if monto <= 0:
            raise ValidacionError("El monto a pagar debe ser mayor a 0.")
        if cliente.deuda <= 0:
            raise ConflictoError(f"{cliente.nombre} no tiene deuda pendiente.")
        if monto > cliente.deuda:
            raise ValidacionError(
                f"{cliente.nombre} debe S/ {cliente.deuda}: no se puede cobrar más. "
                "Si deja dinero a cuenta, el administrador lo registra como crédito ya pagado."
            )
        return await self._entrada_a_caja(
            MOV_FIADO_PAGO, cliente, monto, metodo, nota,
            usuario_id, nombre_usuario, rol, ip, user_agent,
        )

    async def registrar_adelanto(
        self, usuario_id: int, nombre_usuario: str, rol: str, cliente_id: int,
        monto, metodo: str, nota: str | None = None, ip: str = "", user_agent: str = "",
    ) -> MovimientoFiado:
        """Crédito YA pagado (solo ADMIN): queda a favor del cliente y entra a la caja."""
        if rol != ROL_ADMIN:
            raise ProhibidoError("Solo el administrador puede asignar crédito.")
        cliente = await self.obtener(cliente_id)
        monto = monto_dinero(monto)
        if monto <= 0:
            raise ValidacionError("El monto del crédito debe ser mayor a 0.")
        return await self._entrada_a_caja(
            MOV_FIADO_ADELANTO, cliente, monto, metodo, nota,
            usuario_id, nombre_usuario, rol, ip, user_agent,
        )

    async def _entrada_a_caja(
        self, tipo: str, cliente: ClienteFiado, monto: Decimal, metodo: str, nota: str | None,
        usuario_id: int, nombre_usuario: str, rol: str, ip: str, user_agent: str,
    ) -> MovimientoFiado:
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("Abre un turno de caja: el pago entra a la caja del turno actual.")
        if turno.asignado_a_id and turno.asignado_a_id != usuario_id and rol != ROL_ADMIN:
            raise ProhibidoError("Este turno ha sido asignado a otro cajero.")
        codigo = str(metodo or "").strip().upper()
        info = next(
            (m for m in await self._metodos.listar(solo_activos=True)
             if m.codigo == codigo and m.codigo != METODO_FIADO),
            None,
        )
        if info is None:
            raise ValidacionError(f"Método de pago no válido o inactivo: {codigo or '(vacío)'}.")
        movimiento = await self._repo.registrar_movimiento(
            MovimientoFiado(
                id=None, cliente_id=cliente.id, tipo=tipo, monto=monto,
                saldo_resultante=Decimal("0"), usuario_id=usuario_id,
                registrado_por=nombre_usuario, turno_id=turno.id,
                metodo_pago_id=info.id, codigo_metodo=info.codigo,
                es_efectivo=info.es_efectivo, entra_a_caja=True,
                nota=(nota or "").strip() or None, cliente_nombre=cliente.nombre,
            ),
            delta_saldo=monto,
        )
        await self._auditoria.ejecutar(
            accion="fiado_pago" if tipo == MOV_FIADO_PAGO else "fiado_credito_pagado",
            entidad="clientes_fiado", entidad_id=cliente.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={
                "monto": float(monto), "metodo": info.codigo, "turno_id": turno.id,
                "saldo": float(movimiento.saldo_resultante),
            },
            motivo=movimiento.nota, ip=ip, user_agent=user_agent,
        )
        return movimiento

    # ------------------------------------------------------------------ usado por ventas
    async def cliente_para_fiar(self, cliente_id: int | None) -> ClienteFiado:
        if cliente_id is None:
            raise ValidacionError("Para fiar hay que elegir el cliente.")
        cliente = await self.obtener(cliente_id)
        if not cliente.activo:
            raise ValidacionError(f"{cliente.nombre} está desactivado: no se le puede fiar.")
        return cliente

    async def cargar_consumo(
        self, cliente: ClienteFiado, monto: Decimal, venta_id: int, turno_id: int,
        usuario_id: int, nombre_usuario: str,
    ) -> str | None:
        """Carga lo fiado a la cuenta. Devuelve un aviso si con esto pasa su
        límite mensual (no bloquea: la venta ya se hizo)."""
        await self._repo.registrar_movimiento(
            MovimientoFiado(
                id=None, cliente_id=cliente.id, tipo=MOV_FIADO_CONSUMO, monto=monto,
                saldo_resultante=Decimal("0"), usuario_id=usuario_id,
                registrado_por=nombre_usuario, venta_id=venta_id, turno_id=turno_id,
                codigo_metodo=METODO_FIADO, cliente_nombre=cliente.nombre,
            ),
            delta_saldo=-monto,
        )
        consumo = cliente.consumo_mes + monto
        if consumo <= cliente.limite_mensual:
            return None
        aviso = (
            f"{cliente.nombre} lleva S/ {consumo} fiado este mes "
            f"y su límite es S/ {cliente.limite_mensual}."
        )
        # Se avisa a la administradora solo al CRUZAR el límite, no en cada venta.
        if cliente.consumo_mes <= cliente.limite_mensual and self._notificador is not None:
            from app.modules.modulo_d_documentos.domain.value_objects import TipoNotificacion

            await self._notificador.avisar(
                TipoNotificacion.SISTEMA,
                f"Fiado sobre el límite: {cliente.nombre}",
                aviso + f" Venta #{venta_id}, registrada por {nombre_usuario}.",
                entidad_origen="clientes_fiado",
                entidad_id=cliente.id,
            )
        return aviso

    async def revertir_de_venta(
        self, venta_id: int, monto_max: Decimal, anulacion_id: int, turno_id: int,
        usuario_id: int, nombre_usuario: str,
    ) -> Decimal:
        """Anulación/devolución de una venta fiada: primero se descuenta de la
        deuda (lo que aún no se pagó). Devuelve cuánto se revirtió."""
        cliente_id, pendiente = await self._repo.fiado_pendiente_de_venta(venta_id)
        revertir = min(monto_max, pendiente)
        if cliente_id is None or revertir <= 0:
            return Decimal("0")
        await self._repo.registrar_movimiento(
            MovimientoFiado(
                id=None, cliente_id=cliente_id, tipo=MOV_FIADO_REVERSO, monto=revertir,
                saldo_resultante=Decimal("0"), usuario_id=usuario_id,
                registrado_por=nombre_usuario, venta_id=venta_id,
                anulacion_id=anulacion_id, turno_id=turno_id, codigo_metodo=METODO_FIADO,
            ),
            delta_saldo=revertir,
        )
        return revertir

    async def pendiente_de_venta(self, venta_id: int) -> Decimal:
        _cliente, pendiente = await self._repo.fiado_pendiente_de_venta(venta_id)
        return pendiente
