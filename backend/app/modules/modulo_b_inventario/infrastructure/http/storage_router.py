# Router HTTP: subida y lectura de la foto de boleta (Google Drive).
from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_auditoria,
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    StorageUploadResponse,
)

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.post("/upload", response_model=StorageUploadResponse, status_code=201)
async def upload(
    request: Request,
    carpeta: str = Form(...),
    file: UploadFile = File(...),
    usuario: Usuario = Depends(require_permission("storage.upload")),
    db=Depends(__import__("app.shared.database.session", fromlist=["get_db"]).get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    content = await file.read()
    resultado = await contenedor.subir_archivo_usecase(db).ejecutar(
        carpeta=carpeta,
        filename_original=file.filename or "archivo",
        content=content,
        mime=file.content_type or "application/octet-stream",
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return StorageUploadResponse(
        url=resultado.url,
        path=resultado.path,
        filename=resultado.filename,
        mime=resultado.mime,
        size_bytes=resultado.size_bytes,
    )


# Tipo de imagen a partir de los bytes: Drive no siempre devuelve un
# content-type útil y el nombre del archivo no viaja hasta acá.
def _tipo_de_imagen(contenido: bytes) -> str:
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return "application/octet-stream"


@router.get("/boleta/{file_id}")
async def ver_boleta(
    file_id: str,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db=Depends(__import__("app.shared.database.session", fromlist=["get_db"]).get_db),
):
    """Devuelve la imagen de una boleta leyéndola de Drive con las credenciales
    del negocio.

    Existe porque depender del enlace público de Drive es frágil: cuál de sus
    formatos de URL sirve la imagen ha ido cambiando, y todos exigen que el
    archivo esté compartido con "cualquiera con el enlace". Por acá la boleta
    llega siempre y sólo a quien tiene sesión y permiso.
    """
    contenido = await contenedor.drive(db).descargar(file_id)
    return Response(
        content=contenido,
        media_type=_tipo_de_imagen(contenido),
        # Privado: es material contable, no debe quedar en caches compartidas.
        headers={"Cache-Control": "private, max-age=3600"},
    )
