# Casos de uso del fiado (RF-28): clientes, consulta de deudas y abonos.
#
# Regla central: el fiado descuenta stock pero NO suma dinero a la caja; cuando
# el cliente paga (abono), ESE dinero sí entra — y si es efectivo, cuenta para
# el arqueo del turno en el que se cobró. Todo deja rastro para la administradora.
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import Abono, Cliente, Fiado
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.fiado_repository_port import FiadoRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.metodo_pago_repository_port import (
    MetodoPagoRepositoryPort,
)
from app.modules.modulo_c_ventas.domain.value_objects import METODO_FIADO, monto_dinero
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError, ValidacionError


class GestionarClientesUseCase:
    def __init__(self, fiado_repo: FiadoRepositoryPort, auditoria: RegistrarAuditoriaUseCase):
        self._fiados = fiado_repo
        self._auditoria = auditoria

    async def listar(self, busqueda: str | None = None) -> list[Cliente]:
        return await self._fiados.listar_clientes(busqueda)

    async def crear(
        self, usuario_id: int, rol: str, nombre: str, alias: str | None,
        telefono: str | None, ip: str = "", user_agent: str = "",
    ) -> Cliente:
        if not nombre.strip():
            raise ValidacionError("El nombre del cliente no puede estar vacío.")
        creado = await self._fiados.crear_cliente(
            Cliente(id=None, nombre=nombre.strip(), alias=alias, telefono=telefono)
        )
        await self._auditoria.ejecutar(
            accion="cliente_creado", entidad="clientes", entidad_id=creado.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={"nombre": creado.nombre, "alias": creado.alias},
            ip=ip, user_agent=user_agent,
        )
        return creado

    async def actualizar(
        self, usuario_id: int, rol: str, cliente_id: int, cambios: dict,
        ip: str = "", user_agent: str = "",
    ) -> Cliente:
        actual = await self._fiados.buscar_cliente(cliente_id)
        if actual is None:
            raise NoEncontradoError("Cliente no encontrado.")
        if "limite_credito" in cambios and cambios["limite_credito"] is not None:
            cambios["limite_credito"] = monto_dinero(cambios["limite_credito"])
        actualizado = await self._fiados.actualizar_cliente(cliente_id, cambios)
        await self._auditoria.ejecutar(
            accion="cliente_editado", entidad="clientes", entidad_id=cliente_id,
            usuario_id=usuario_id, rol=rol,
            valor_anterior={"nombre": actual.nombre, "limite_credito": float(actual.limite_credito)},
            valor_nuevo={
                k: (float(v) if isinstance(v, Decimal) else v)
                for k, v in cambios.items() if v is not None
            },
            ip=ip, user_agent=user_agent,
        )
        return actualizado


class ConsultarFiadosUseCase:
    def __init__(self, fiado_repo: FiadoRepositoryPort):
        self._fiados = fiado_repo

    async def listar(
        self, cliente_id: int | None = None, solo_pendientes: bool = True
    ) -> list[Fiado]:
        return await self._fiados.listar_fiados(cliente_id, solo_pendientes)

    async def abonos(self, fiado_id: int) -> list[Abono]:
        if await self._fiados.buscar_fiado(fiado_id) is None:
            raise NoEncontradoError("Fiado no encontrado.")
        return await self._fiados.abonos_de_fiado(fiado_id)


class RegistrarAbonoUseCase:
    def __init__(
        self,
        fiado_repo: FiadoRepositoryPort,
        caja_repo: CajaRepositoryPort,
        metodos_repo: MetodoPagoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._fiados = fiado_repo
        self._caja = caja_repo
        self._metodos = metodos_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        fiado_id: int,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        monto,
        codigo_metodo: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Fiado:
        fiado = await self._fiados.buscar_fiado(fiado_id)
        if fiado is None:
            raise NoEncontradoError("Fiado no encontrado.")
        if fiado.estado != "PENDIENTE":
            raise ConflictoError("Este fiado ya está saldado.")

        # El dinero del abono entra a la caja del turno actual (RF-17).
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("Abre un turno de caja para poder cobrar el abono.")

        codigo = codigo_metodo.strip().upper()
        if codigo == METODO_FIADO:
            raise ValidacionError("Un abono no puede pagarse con fiado.")
        metodo = await self._metodos.buscar_por_codigo(codigo)
        if metodo is None or not metodo.activo:
            raise ValidacionError(f"Método de pago no válido o inactivo: {codigo}.")

        monto = monto_dinero(monto)
        if monto <= 0:
            raise ValidacionError("El abono debe ser mayor a 0.")
        if monto > fiado.saldo_pendiente:
            raise ValidacionError(
                f"El abono (S/ {monto}) supera el saldo pendiente (S/ {fiado.saldo_pendiente})."
            )

        nuevo_saldo = monto_dinero(fiado.saldo_pendiente - monto)
        nuevo_estado = "PAGADO" if nuevo_saldo == 0 else "PENDIENTE"
        await self._fiados.crear_abono(
            Abono(
                id=None, fiado_id=fiado_id, turno_id=turno.id, usuario_id=usuario_id,
                registrado_por=nombre_usuario, codigo_metodo=codigo,
                es_efectivo=metodo.es_efectivo, monto=monto, metodo_pago_id=metodo.id,
            )
        )
        await self._fiados.actualizar_saldo(fiado_id, nuevo_saldo, nuevo_estado)

        await self._auditoria.ejecutar(
            accion="abono_registrado", entidad="fiados", entidad_id=fiado_id,
            usuario_id=usuario_id, rol=rol,
            valor_anterior={"saldo_pendiente": float(fiado.saldo_pendiente)},
            valor_nuevo={
                "abono": float(monto), "metodo": codigo,
                "saldo_pendiente": float(nuevo_saldo), "estado": nuevo_estado,
                "turno_id": turno.id,
            },
            ip=ip, user_agent=user_agent,
        )
        return await self._fiados.buscar_fiado(fiado_id)
