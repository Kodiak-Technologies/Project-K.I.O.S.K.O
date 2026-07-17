# Modelos SQLAlchemy (tablas) del módulo de ventas: ventas, detalles, cajas, aperturas, cierres.
# Nombres en español y snake_case. Todas las fechas TIMESTAMPTZ. Montos NUMERIC(10,2).
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base_model import Base


class TurnoCajaModel(Base):
    __tablename__ = "turnos_caja"
    __table_args__ = (
        CheckConstraint("monto_inicial >= 0", name="ck_turnos_monto_inicial_no_negativo"),
        # Solo puede existir UN turno abierto a la vez (una caja física en la tienda).
        Index(
            "ux_turnos_caja_abierto",
            "estado",
            unique=True,
            postgresql_where=text("estado = 'ABIERTO'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # RESTRICT: un usuario con turnos no puede desaparecer — preserva trazabilidad.
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    abierto_por: Mapped[str] = mapped_column(String(100), nullable=False)  # snapshot del nombre
    monto_inicial: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), default="ABIERTO", nullable=False)
    abierto_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    monto_final: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    usuario_cierre_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    cerrado_por: Mapped[str | None] = mapped_column(String(100))
