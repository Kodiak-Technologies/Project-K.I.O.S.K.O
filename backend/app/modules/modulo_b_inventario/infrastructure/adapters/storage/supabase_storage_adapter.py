# Adaptador: implementa StoragePort usando el SDK de Supabase (`supabase-py`).
# Stub de PR1: la implementación real se hace en PR2.
#
# Variables de entorno requeridas en runtime (NO validadas acá; el adapter las
# lee en PR2 cuando se implemente `subir()`):
#   - SUPABASE_URL=https://<project>.supabase.co
#   - SUPABASE_SERVICE_ROLE_KEY=<service-role-key>  # NO la anon key
#   - SUPABASE_STORAGE_BUCKET_BOLETAS=boletas
#   - SUPABASE_STORAGE_BUCKET_PRODUCTOS=productos
#
# Decisiones:
#   - D-T01: SDK `supabase-py` (no `httpx` directo); fallback a `httpx` si el SDK
#     no expone `create_signed_url` con expiración exacta.
#   - Q2 (proposal): para bucket `boletas` (privado) → signed URL con expiración
#     de 24h (86400 s). Para bucket `productos` (público) → URL pública.
#   - D-T07 R2: en tests se mockea este puerto con un `InMemoryStorageAdapter`.
#
# NOTA: `supabase` NO está en `pyproject.toml` (no se instaló en este PR); el
# import se hace dentro de `subir()` en PR2 para que el módulo sea importable
# aunque el paquete no esté presente.
from typing import TYPE_CHECKING

from app.modules.modulo_b_inventario.domain.ports.storage_port import StoragePort
from app.modules.modulo_b_inventario.domain.value_objects import StorageResult

if TYPE_CHECKING:
    from app.shared.config.settings import Settings


class SupabaseStorageAdapter(StoragePort):
    """Stub. En PR2 usará `supabase.create_client(url, service_role_key)`."""

    def __init__(self, settings: "Settings | None" = None) -> None:
        # El parámetro `settings` se acepta pero no se usa en el stub.
        # En PR2 se validan `settings.supabase_url` y `settings.supabase_service_role_key`.
        self._settings = settings

    async def subir(self, carpeta, filename, content, mime) -> StorageResult:
        raise NotImplementedError(
            "Implementado en PR2 — usa el SDK supabase-py y signed URL de 24h "
            "para bucket 'boletas' (privado) o public URL para 'productos' (público)."
        )
