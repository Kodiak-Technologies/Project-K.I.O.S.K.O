"""Módulo B (completo): proveedores, ingresos, mermas, movimientos, pagos e historial.

Faltaba por completo en la cadena de migraciones: estas 7 tablas (y las columnas
nuevas de `productos`/`categorias`) solo existían en `db/schema_modulo_b_completo.sql`,
que se aplica a mano con `python -m scripts.aplicar_schema`. En un entorno nuevo,
`alembic upgrade head` dejaba la BD sin el Módulo B y la migración
`0013_modulo_b_editar_ingreso_merma` fallaba al hacer ADD COLUMN sobre
`solicitudes_ingreso`, que no existía.

Esta revisión ejecuta el MISMO script canónico de `db/` (idempotente:
`CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`) recortando la
"Sección 3.5", que es justamente lo que aplica la 0013 (si no, la 0013 se
encontraría las columnas ya creadas y su `add_column` explotaría).

Revision ID: 0012a_modulo_b_esquema
Revises: 0012_modulo_d_reestructuracion
Create Date: 2026-07-25
"""
from pathlib import Path

from alembic import op


# revision identifiers, used by Alembic.
revision = "0012a_modulo_b_esquema"
down_revision = "0012_modulo_d_reestructuracion"
branch_labels = None
depends_on = None

# Fuente única de verdad del DDL del módulo (la misma que usa scripts/aplicar_schema.py).
ARCHIVO_DDL = Path(__file__).resolve().parents[2] / "db" / "schema_modulo_b_completo.sql"
MARCA_SECCION_0013 = "-- Sección 3.5 (sdd/modulo-b-aprobaciones-detalle-editar):"


def upgrade() -> None:
    sql = ARCHIVO_DDL.read_text(encoding="utf-8")
    # Recorte: todo lo anterior a la Sección 3.5 (esa la aplica la 0013).
    corte = sql.find(MARCA_SECCION_0013)
    if corte != -1:
        # Retrocede hasta el inicio del bloque de comentarios de la sección.
        inicio_bloque = sql.rfind("-- ----", 0, corte)
        sql = sql[: inicio_bloque if inicio_bloque != -1 else corte]
    op.execute(sql)


def downgrade() -> None:
    # Bajada destructiva: se eliminan las tablas del módulo en orden inverso a
    # sus FKs. Las columnas agregadas a `productos`/`categorias` se conservan
    # (son aditivas y el Módulo C lee esas tablas).
    for tabla in (
        "movimientos_inventario",
        "historial_precios",
        "pagos_proveedor",
        "detalle_solicitud",
        "mermas",
        "solicitudes_ingreso",
        "proveedores",
    ):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
