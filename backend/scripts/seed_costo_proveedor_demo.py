# Datos de demostración para el reporte "Costo por proveedor".
#
# Crea solicitudes de ingreso APROBADAS repartidas entre varios proveedores, más
# una SIN proveedor asignado (que en el reporte aparece como "Sin proveedor").
# Es lo único que ese reporte lee: no hay tabla de gastos, el costo y la
# asociación al proveedor viven en `solicitudes_ingreso` + `detalle_solicitud`.
#
# NO toca stock ni `movimientos_inventario` a propósito: la aprobación real pasa
# por el caso de uso, que sí mueve inventario. Acá solo se necesitan filas para
# que el reporte tenga qué agrupar, y así el seed queda trivialmente reversible.
#
# Idempotente: todas las filas que crea llevan MARCA en `motivo`. Si ya hay
# solicitudes con esa marca, no vuelve a insertar.
#
# Uso:      python -m scripts.seed_costo_proveedor_demo
# Deshacer: python -m scripts.seed_costo_proveedor_demo --borrar
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    UsuarioModel,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    DetalleSolicitudModel,
    ProductoModel,
    ProveedorModel,
    SolicitudIngresoModel,
)
from app.shared.database.session import SessionLocal, engine

#: Marca que identifica TODO lo que crea este script. Permite borrarlo sin
#: tocar datos reales.
MARCA = "[demo costo-proveedor]"

#: (razón social, RUC). Se crean solo si no existen (se buscan por RUC).
PROVEEDORES = [
    ("Distribuidora Lima Norte S.A.C.", "20512345678"),
    ("Abarrotes El Sol E.I.R.L.", "20487654321"),
    ("Comercial Andina S.A.", "20456789012"),
]

#: (proveedor o None, días atrás, [(cantidad, total de línea), ...])
#: El None es a propósito: es el caso "Sin proveedor" del reporte.
INGRESOS = [
    ("Distribuidora Lima Norte S.A.C.", 2, [(24, "180.00"), (12, "96.50")]),
    ("Distribuidora Lima Norte S.A.C.", 9, [(36, "240.00")]),
    ("Abarrotes El Sol E.I.R.L.", 4, [(18, "132.00"), (6, "45.00")]),
    ("Abarrotes El Sol E.I.R.L.", 15, [(10, "78.90")]),
    ("Comercial Andina S.A.", 6, [(48, "310.00")]),
    (None, 3, [(8, "64.00")]),
    (None, 11, [(15, "112.50")]),
]


async def _borrar(db) -> None:
    ids = (
        (
            await db.execute(
                select(SolicitudIngresoModel.id).where(
                    SolicitudIngresoModel.motivo == MARCA
                )
            )
        )
        .scalars()
        .all()
    )
    if not ids:
        print("No hay datos de demo que borrar.")
        return
    # Las líneas primero: la FK es ON DELETE CASCADE, pero se borran explícito
    # para que el conteo sea visible y no dependa del comportamiento de la BD.
    await db.execute(
        delete(DetalleSolicitudModel).where(
            DetalleSolicitudModel.solicitud_id.in_(ids)
        )
    )
    await db.execute(
        delete(SolicitudIngresoModel).where(SolicitudIngresoModel.id.in_(ids))
    )
    await db.commit()
    print(f"Borradas {len(ids)} solicitudes de demo (y sus líneas).")
    print("Los proveedores creados NO se borran: pueden tener otros datos colgando.")


async def sembrar(borrar: bool = False) -> None:
    async with SessionLocal() as db:
        if borrar:
            await _borrar(db)
            await engine.dispose()
            return

        ya_hay = (
            await db.execute(
                select(SolicitudIngresoModel.id)
                .where(SolicitudIngresoModel.motivo == MARCA)
                .limit(1)
            )
        ).scalar_one_or_none()
        if ya_hay is not None:
            print("Los datos de demo ya están cargados. Nada que hacer.")
            print("Para regenerarlos: python -m scripts.seed_costo_proveedor_demo --borrar")
            await engine.dispose()
            return

        usuario = (
            await db.execute(select(UsuarioModel).order_by(UsuarioModel.id).limit(1))
        ).scalar_one_or_none()
        if usuario is None:
            print("ABORTADO: no hay usuarios. Corre primero `python -m scripts.seed`.")
            await engine.dispose()
            return

        productos = (
            (
                await db.execute(
                    select(ProductoModel)
                    .where(ProductoModel.deleted_at.is_(None))
                    .order_by(ProductoModel.id)
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )
        if not productos:
            print("ABORTADO: no hay productos. Corre primero `python -m scripts.seed_demo`.")
            await engine.dispose()
            return

        # Proveedores: se buscan por RUC, se crean si faltan.
        por_nombre: dict[str, ProveedorModel] = {}
        nuevos_prov = 0
        for razon_social, ruc in PROVEEDORES:
            prov = (
                await db.execute(
                    select(ProveedorModel).where(
                        ProveedorModel.ruc == ruc,
                        ProveedorModel.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if prov is None:
                prov = ProveedorModel(
                    razon_social=razon_social,
                    ruc=ruc,
                    activo=True,
                    creado_por=usuario.id,
                    creado_por_nombre=usuario.nombre,
                )
                db.add(prov)
                await db.flush()
                nuevos_prov += 1
            por_nombre[razon_social] = prov

        ahora = datetime.now(timezone.utc)
        nuevas_sol = 0
        nuevas_lineas = 0
        for nombre_prov, dias_atras, lineas in INGRESOS:
            revisado_en = ahora - timedelta(days=dias_atras)
            solicitud = SolicitudIngresoModel(
                proveedor_id=por_nombre[nombre_prov].id if nombre_prov else None,
                estado="Aprobada",
                foto_boleta_url="",
                motivo=MARCA,
                solicitado_por=usuario.id,
                solicitado_por_nombre=usuario.nombre,
                revisado_por=usuario.id,
                revisado_por_nombre=usuario.nombre,
                revisado_en=revisado_en,
            )
            db.add(solicitud)
            await db.flush()
            nuevas_sol += 1

            for idx, (cantidad, total) in enumerate(lineas):
                db.add(
                    DetalleSolicitudModel(
                        solicitud_id=solicitud.id,
                        producto_id=productos[
                            (nuevas_sol + idx) % len(productos)
                        ].id,
                        cantidad=cantidad,
                        precio_compra_total=Decimal(total),
                    )
                )
                nuevas_lineas += 1

        await db.commit()

        total = sum(
            Decimal(t) for _, _, lineas in INGRESOS for _, t in lineas
        )
        sin_prov = sum(
            Decimal(t) for nombre, _, lineas in INGRESOS if nombre is None for _, t in lineas
        )
        print(f"Proveedores creados : {nuevos_prov:>3} (de {len(PROVEEDORES)})")
        print(f"Solicitudes creadas : {nuevas_sol:>3} (aprobadas, últimos 15 días)")
        print(f"Líneas creadas      : {nuevas_lineas:>3}")
        print(f"Costo total         : S/ {total}")
        print(f"  de ellos sin proveedor: S/ {sin_prov}")
        print()
        print("Para deshacer: python -m scripts.seed_costo_proveedor_demo --borrar")

    await engine.dispose()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sembrar(borrar="--borrar" in sys.argv))
