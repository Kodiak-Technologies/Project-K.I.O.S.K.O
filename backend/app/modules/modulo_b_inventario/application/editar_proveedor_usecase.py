# Caso de uso: editar un proveedor (HU-B14, REQ-PROV-04).
# - NO permite modificar deuda_actual (422 → usar /compras-credito o /pagos).
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class EditarProveedorUseCase:
    def __init__(
        self,
        proveedor_repo: ProveedorRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._proveedores = proveedor_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        proveedor_id: int,
        cambios: dict,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Proveedor:
        if "deuda_actual" in cambios:
            raise ValidacionError(
                "deuda_actual solo se modifica vía compras a crédito o pagos."
            )
        anterior = await self._proveedores.find_by_id(proveedor_id)
        # Antes, si el proveedor no existía (o estaba borrado lógicamente) se
        # construía una entidad con "" / None y el UPDATE PISABA los datos reales.
        if anterior is None:
            raise NoEncontradoError("Proveedor no encontrado.")
        actualizado = await self._proveedores.actualizar(
            Proveedor(
                id=proveedor_id,
                razon_social=cambios.get("razon_social") or anterior.razon_social,
                creado_por=anterior.creado_por,
                creado_por_nombre=anterior.creado_por_nombre,
                ruc=cambios.get("ruc", anterior.ruc),
                telefono=cambios.get("telefono", anterior.telefono),
                email=cambios.get("email", anterior.email),
                direccion=cambios.get("direccion", anterior.direccion),
                activo=cambios.get("activo", anterior.activo)
                if cambios.get("activo") is not None
                else anterior.activo,
                deuda_actual=anterior.deuda_actual,
            )
        )
        await self._auditoria.ejecutar(
            accion="proveedor_editado",
            entidad="proveedores",
            usuario_id=usuario_id,
            rol="",
            entidad_id=proveedor_id,
            valor_anterior={
                "razon_social": anterior.razon_social if anterior else None,
                "ruc": anterior.ruc if anterior else None,
            } if anterior else None,
            valor_nuevo={k: v for k, v in cambios.items() if v is not None},
            ip=ip,
            user_agent=user_agent,
        )
        return actualizado
