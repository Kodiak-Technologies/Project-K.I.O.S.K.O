# Router HTTP: /storage/upload — subida de archivos a Supabase Storage.
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_auditoria,
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    RefirmarRequest,
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
        expires_at=resultado.expires_at,
    )


@router.post("/firmar", response_model=StorageUploadResponse)
async def refirmar(
    datos: RefirmarRequest,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db=Depends(__import__("app.shared.database.session", fromlist=["get_db"]).get_db),
):
    """Devuelve la URL de una boleta ya subida a partir de su id de Drive.

    Existía porque las URLs firmadas de Supabase vencían (HU-B07). Con Drive el
    enlace es permanente; se conserva para no romper a quien ya lo llame.
    """
    resultado = await contenedor.refirmar_archivo(db, datos.carpeta, datos.path)
    return StorageUploadResponse(
        url=resultado.url,
        path=resultado.path,
        filename=resultado.filename,
        mime=resultado.mime,
        size_bytes=resultado.size_bytes,
        expires_at=resultado.expires_at,
    )
