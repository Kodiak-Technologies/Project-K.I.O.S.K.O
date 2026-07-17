# Modelos SQLAlchemy (tablas) del módulo de inventario: productos, categorías, almacenes, ingresos, movimientos.
#
# NOTA (Clever): implementación MÍNIMA de productos/categorías según el contrato de
# docs/FRONTEND_CONTRATOS_API.md, para que el POS (Módulo C) sea probable de punta a punta.
# Brayan la reemplaza/amplía con su implementación completa del Módulo B.
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base_model import Base
from app.shared.kernel.soft_delete import SoftDeleteMixin


class CategoriaModel(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class ProductoModel(Base, SoftDeleteMixin):
    __tablename__ = "productos"
    __table_args__ = (
        # El stock NUNCA queda negativo (RF-08): reforzado también a nivel de BD.
        CheckConstraint("stock >= 0", name="ck_productos_stock_no_negativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Código de barras escaneado o código interno (PAP-001). Único en todo el catálogo.
    codigo: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id", ondelete="RESTRICT")
    )
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
