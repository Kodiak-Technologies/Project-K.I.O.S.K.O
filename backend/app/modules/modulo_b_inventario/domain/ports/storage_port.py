# Puerto: contrato para subir archivos a Supabase Storage (HU-B foto boleta, foto producto).
# Decisión D-T01: el adaptador usa el SDK `supabase-py` (D-T07 R2: en tests se mockea).
from abc import ABC, abstractmethod
from typing import Literal

from app.modules.modulo_b_inventario.domain.value_objects import StorageResult


class StoragePort(ABC):
    """Puerto de subida de archivos.

    Variables de entorno requeridas en runtime (documentadas en
    `supabase_storage_adapter.py`):
      - SUPABASE_URL
      - SUPABASE_SERVICE_ROLE_KEY (NO anon)
      - SUPABASE_STORAGE_BUCKET_BOLETAS=boletas
      - SUPABASE_STORAGE_BUCKET_PRODUCTOS=productos
    """

    @abstractmethod
    async def subir(
        self,
        carpeta: Literal["boletas", "productos"],
        filename: str,
        content: bytes,
        mime: str,
    ) -> StorageResult:
        """Sube el archivo y devuelve URL + path. Para `boletas` la URL es
        firmada (TTL configurable, 1 año por defecto); para `productos` es pública.
        """

    async def refirmar(
        self, carpeta: Literal["boletas", "productos"], path: str
    ) -> StorageResult:
        """Regenera la URL de un archivo ya subido a partir de su `path`.

        No es abstracto para no romper adaptadores en memoria de los tests;
        el adaptador real lo implementa.
        """
        raise NotImplementedError
