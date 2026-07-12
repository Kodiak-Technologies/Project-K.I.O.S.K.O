# Helper transversal de borrado lógico, reutilizable por los módulos B, C y D en sus modelos SQLAlchemy.
# Regla del sistema: NINGUNA eliminación es física (RNF). Se marca deleted_at/deleted_by.
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """Mixin para modelos SQLAlchemy: agrega deleted_at y deleted_by.

    Uso en cualquier módulo:

        class Producto(Base, SoftDeleteMixin):
            __tablename__ = "productos"
            ...

    Y para "eliminar":  marcar_borrado(producto, usuario_actual.id)
    Las consultas normales deben filtrar con `.where(Modelo.deleted_at.is_(None))`.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_by: Mapped[int | None] = mapped_column(BigInteger, default=None)


def marcar_borrado(modelo: SoftDeleteMixin, usuario_id: int) -> None:
    """Marca la fila como borrada lógicamente. Nunca emitir DELETE físico."""
    modelo.deleted_at = datetime.now(timezone.utc)
    modelo.deleted_by = usuario_id
