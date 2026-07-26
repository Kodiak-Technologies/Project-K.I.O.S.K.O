# Caso de uso: subir un archivo a Supabase Storage (REQ-STO).
# - Valida MIME (image/jpeg | image/png) y tamaño (<= 10 MB).
# - Genera path único {carpeta}/{YYYY-MM-DD}-{uuid}.{ext}.
# - Llama al StoragePort.
from __future__ import annotations

import uuid
from datetime import date

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.ports.storage_port import StoragePort
from app.modules.modulo_b_inventario.domain.value_objects import StorageResult
from app.shared.kernel.exceptions import ValidacionError


class SubirArchivoUseCase:
    TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB
    MIMES_PERMITIDOS = {"image/jpeg", "image/png"}
    # Solo boletas: los productos ya no llevan foto (decisión 2026-07-25).
    CARPETAS_VALIDAS = ("boletas",)
    EXTENSION_POR_MIME = {
        "image/jpeg": "jpg",
        "image/png": "png",
    }

    def __init__(
        self,
        storage: StoragePort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._storage = storage
        self._auditoria = auditoria

    async def ejecutar(
        self,
        *,
        carpeta: str,
        filename_original: str,
        content: bytes,
        mime: str,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> StorageResult:
        if carpeta not in self.CARPETAS_VALIDAS:
            raise ValidacionError(
                f"Carpeta inválida. Permitidas: {', '.join(self.CARPETAS_VALIDAS)}."
            )
        if mime not in self.MIMES_PERMITIDOS:
            raise ValidacionError(
                "Tipo de archivo no soportado. Solo JPEG y PNG."
            )
        if not content:
            raise ValidacionError("El archivo está vacío.")
        if len(content) > self.TAMANO_MAXIMO_BYTES:
            raise ValidacionError(
                "El archivo supera el tamaño máximo permitido (10 MB)."
            )
        ext = self.EXTENSION_POR_MIME[mime]
        fecha = date.today().strftime("%Y-%m-%d")
        uid = uuid.uuid4().hex[:12]
        path = f"{carpeta}/{fecha}-{uid}.{ext}"
        resultado = await self._storage.subir(carpeta, path, content, mime)
        await self._auditoria.ejecutar(
            accion="storage_upload",
            entidad="storage",
            usuario_id=usuario_id,
            rol="",
            entidad_id=None,
            valor_nuevo={
                "carpeta": carpeta,
                "filename": resultado.filename,
                "size_bytes": resultado.size_bytes,
                "mime": mime,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return resultado
