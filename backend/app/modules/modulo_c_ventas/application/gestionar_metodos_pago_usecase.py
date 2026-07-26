# Caso de uso: gestionar el catálogo de métodos de pago (RF-20).
# El ADMIN puede agregar métodos nuevos (ej. una nueva billetera) o desactivar
# alguno sin tocar código; EFECTIVO no se puede desactivar porque la caja
# (RF-17) depende de él.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import MetodoPago
from app.modules.modulo_c_ventas.domain.ports.metodo_pago_repository_port import (
    MetodoPagoRepositoryPort,
)
from app.modules.modulo_c_ventas.domain.value_objects import METODO_EFECTIVO
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError, ValidacionError

PROTEGIDOS = {METODO_EFECTIVO}


class GestionarMetodosPagoUseCase:
    def __init__(self, repo: MetodoPagoRepositoryPort, auditoria: RegistrarAuditoriaUseCase):
        self._metodos = repo
        self._auditoria = auditoria

    async def listar(self, solo_activos: bool = True) -> list[MetodoPago]:
        return await self._metodos.listar(solo_activos)

    async def crear(
        self, admin_id: int, rol: str, codigo: str, nombre: str, es_efectivo: bool,
        ip: str = "", user_agent: str = "",
    ) -> MetodoPago:
        codigo = codigo.strip().upper().replace(" ", "_")
        if not codigo:
            raise ValidacionError("El código del método de pago no puede estar vacío.")
        if await self._metodos.buscar_por_codigo(codigo) is not None:
            raise ConflictoError(f"Ya existe el método de pago '{codigo}'.")
        creado = await self._metodos.crear(
            MetodoPago(id=None, codigo=codigo, nombre=nombre.strip(), es_efectivo=es_efectivo)
        )
        await self._auditoria.ejecutar(
            accion="metodo_pago_creado", entidad="metodos_pago", entidad_id=creado.id,
            usuario_id=admin_id, rol=rol,
            valor_nuevo={"codigo": creado.codigo, "nombre": creado.nombre, "es_efectivo": es_efectivo},
            ip=ip, user_agent=user_agent,
        )
        return creado

    async def actualizar(
        self, admin_id: int, rol: str, metodo_id: int, cambios: dict,
        ip: str = "", user_agent: str = "",
    ) -> MetodoPago:
        actuales = {m.id: m for m in await self._metodos.listar(solo_activos=False)}
        actual = actuales.get(metodo_id)
        if actual is None:
            raise NoEncontradoError("Método de pago no encontrado.")
        if actual.codigo in PROTEGIDOS and cambios.get("activo") is False:
            raise ValidacionError(f"El método {actual.codigo} no se puede desactivar.")
        actualizado = await self._metodos.actualizar(metodo_id, cambios)
        await self._auditoria.ejecutar(
            accion="metodo_pago_editado", entidad="metodos_pago", entidad_id=metodo_id,
            usuario_id=admin_id, rol=rol,
            valor_anterior={"nombre": actual.nombre, "activo": actual.activo},
            valor_nuevo={k: v for k, v in cambios.items() if v is not None},
            ip=ip, user_agent=user_agent,
        )
        return actualizado
