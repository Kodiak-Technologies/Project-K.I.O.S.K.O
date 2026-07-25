# Adaptador: implementa StoragePort contra el REST de Supabase Storage usando httpx.
# NO requiere el SDK `supabase-py` (no instalado); usa httpx directo.
#
# Variables de entorno requeridas en runtime (leídas acá, NO en el módulo al importarse
# para no romper tests ni el import del módulo si faltan):
#   - SUPABASE_URL=https://<project>.supabase.co
#   - SUPABASE_SERVICE_ROLE_KEY=<service-role-key>  # NO la anon key
#   - SUPABASE_STORAGE_BUCKET_BOLETAS=boletas
#   - SUPABASE_STORAGE_BUCKET_PRODUCTOS=productos
#
# Decisiones:
#   - D-T01 (override PR2): se usa httpx en vez del SDK (no se instaló supabase-py).
#   - Q2 (proposal): para bucket `boletas` (privado) → signed URL con expiración
#     de 24h (86400 s). Para bucket `productos` (público) → URL pública.
#   - D-T07 R2: en tests se mockea este puerto con un `InMemoryStorageAdapter`.
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx

from app.modules.modulo_b_inventario.domain.ports.storage_port import StoragePort
from app.modules.modulo_b_inventario.domain.value_objects import StorageResult
from app.shared.kernel.exceptions import (
    ErrorDeDominio,
    NoEncontradoError,
    ValidacionError,
)


class SupabaseStorageAdapter(StoragePort):
    """Adaptador de Supabase Storage vía httpx (no usa el SDK)."""

    _CARPETAS_VALIDAS = ("boletas", "productos")

    def __init__(self) -> None:
        self._url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self._key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self._bucket_boletas = os.getenv("SUPABASE_STORAGE_BUCKET_BOLETAS", "boletas")
        self._bucket_productos = os.getenv(
            "SUPABASE_STORAGE_BUCKET_PRODUCTOS", "productos"
        )

    def _bucket_para(self, carpeta: str) -> str:
        if carpeta == "boletas":
            return self._bucket_boletas
        if carpeta == "productos":
            return self._bucket_productos
        raise ValidacionError(f"Carpeta inválida: {carpeta}")

    async def subir(
        self,
        carpeta: Literal["boletas", "productos"],
        filename: str,
        content: bytes,
        mime: str,
    ) -> StorageResult:
        if carpeta not in self._CARPETAS_VALIDAS:
            raise ValidacionError(
                f"Carpeta inválida. Permitidas: {', '.join(self._CARPETAS_VALIDAS)}."
            )
        if not self._url or not self._key:
            raise ErrorDeDominio(
                "Supabase Storage no configurado: faltan SUPABASE_URL o "
                "SUPABASE_SERVICE_ROLE_KEY en el entorno."
            )

        bucket = self._bucket_para(carpeta)
        # Path incluye filename (el caller lo construye como {YYYY-MM-DD}-{uuid}.{ext})
        # pero sanitizamos para evitar path traversal.
        path = filename.lstrip("/")

        # 1) Subir el archivo (upload endpoint)
        upload_url = (
            f"{self._url}/storage/v1/object/{bucket}/{path}"
        )
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": mime,
            "x-upsert": "false",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as cliente:
                respuesta_subida = await cliente.post(
                    upload_url, headers=headers, content=content
                )
        except httpx.HTTPError as exc:
            raise ErrorDeDominio(
                f"No se pudo subir el archivo a Supabase Storage: {exc}"
            ) from exc

        if respuesta_subida.status_code not in (200, 201):
            raise ErrorDeDominio(
                f"Supabase Storage rechazó la subida (HTTP "
                f"{respuesta_subida.status_code}): {respuesta_subida.text[:200]}"
            )

        # 2) Obtener URL final (público o signed)
        if carpeta == "boletas":
            # Privado → signed URL de 24h (Q2, design)
            signed_url = (
                f"{self._url}/storage/v1/object/sign/{bucket}/{path}"
            )
            try:
                async with httpx.AsyncClient(timeout=15.0) as cliente:
                    respuesta_signed = await cliente.post(
                        signed_url,
                        headers={
                            "Authorization": f"Bearer {self._key}",
                            "Content-Type": "application/json",
                        },
                        json={"expiresIn": 86400},
                    )
            except httpx.HTTPError as exc:
                raise ErrorDeDominio(
                    f"No se pudo generar la URL firmada: {exc}"
                ) from exc
            if respuesta_signed.status_code != 200:
                raise ErrorDeDominio(
                    f"Supabase Storage no pudo generar la URL firmada (HTTP "
                    f"{respuesta_signed.status_code}): {respuesta_signed.text[:200]}"
                )
            datos: dict[str, Any] = respuesta_signed.json()
            signed_path = datos.get("signedURL") or datos.get("signed_url")
            if not signed_path:
                raise ErrorDeDominio(
                    "Supabase Storage no devolvió signedURL en la respuesta."
                )
            # La API devuelve la URL relativa, la completamos con la base
            url_final = (
                f"{self._url}{signed_path}"
                if signed_path.startswith("/")
                else signed_path
            )
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=86400)
        else:
            # Público → URL directa al bucket
            url_final = f"{self._url}/storage/v1/object/public/{bucket}/{path}"
            expires_at = None

        return StorageResult(
            url=url_final,
            path=path,
            filename=path.rsplit("/", 1)[-1],
            mime=mime,
            size_bytes=len(content),
            expires_at=expires_at,
        )
