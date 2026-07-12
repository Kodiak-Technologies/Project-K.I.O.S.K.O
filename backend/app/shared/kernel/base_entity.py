# Clases base opcionales para entidades de dominio (Python puro, sin SQLAlchemy).
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EntidadConBorradoLogico:
    """Campos comunes del patrón de borrado lógico transversal (RNF: nada se borra físicamente).

    Una entidad está "eliminada" cuando deleted_at no es None. Los repositorios
    deben excluir esas filas de las consultas normales.
    """

    deleted_at: datetime | None = None
    deleted_by: int | None = None

    @property
    def eliminado(self) -> bool:
        return self.deleted_at is not None
