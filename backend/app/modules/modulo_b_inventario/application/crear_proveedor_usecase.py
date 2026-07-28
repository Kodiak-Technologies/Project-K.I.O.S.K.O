# Caso de uso: crear un proveedor (HU-B14, REQ-PROV).
# - deuda_actual=0 por default.
# - Valida RUC único (parcial: WHERE deleted_at IS NULL).
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    ValidacionError,
)


class CrearProveedorUseCase:
    def __init__(
        self,
        proveedor_repo: ProveedorRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._proveedores = proveedor_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        *,
        razon_social: str,
        ruc: str | None,
        telefono: str | None,
        email: str | None,
        direccion: str | None,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Proveedor:
        razon_social = (razon_social or "").strip()
        if not razon_social:
            raise ValidacionError("La razón social es obligatoria.")
        if ruc and ruc.strip():
            ruc = ruc.strip()
            if await self._proveedores.find_by_ruc(ruc) is not None:
                raise ConflictoError("Ya existe un proveedor con ese RUC.")
        else:
            ruc = None

        creado = await self._proveedores.crear(
            Proveedor(
                id=None,
                razon_social=razon_social,
                creado_por=usuario_id,
                creado_por_nombre=usuario_nombre,
                ruc=ruc,
                telefono=telefono,
                email=email,
                direccion=direccion,
                activo=True,
                deuda_actual=Decimal("0"),
            )
        )
        await self._auditoria.ejecutar(
            accion="proveedor_creado",
            entidad="proveedores",
            usuario_id=usuario_id,
            rol="",
            entidad_id=creado.id,
            valor_nuevo={
                "razon_social": razon_social,
                "ruc": ruc,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return creado
