########################################################
#######    Datos de prueba para el modulo D      #######
########################################################

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import (
    ArchivoDriveModel,
    BoletaModel,
    NotificacionModel,
    RespaldoModel,
)
from app.shared.database.session import SessionLocal, engine

HOY = datetime.now(timezone.utc)


BOLETAS = [
    {"venta_id": 1, "numero": "BOL-2026-0001", "total": 150.00, "dias_atras": 10},
    {"venta_id": 2, "numero": "BOL-2026-0002", "total": 85.50, "dias_atras": 7},
    {"venta_id": 3, "numero": "BOL-2026-0003", "total": 320.00, "dias_atras": 5},
    {"venta_id": 4, "numero": "BOL-2026-0004", "total": 42.75, "dias_atras": 3},
    {"venta_id": 5, "numero": "BOL-2026-0005", "total": 500.00, "dias_atras": 1},
]

ARCHIVOS_DRIVE = [
    {"boleta_idx": 0, "archivo_nombre": "BOL-2026-0001.png", "carpeta": "boletas/2026-07", "estado": "SUBIDO", "drive_file_id": "1ABC_demo_001"},
    {"boleta_idx": 1, "archivo_nombre": "BOL-2026-0002.png", "carpeta": "boletas/2026-07", "estado": "SUBIDO", "drive_file_id": "1ABC_demo_002"},
    {"boleta_idx": 2, "archivo_nombre": "BOL-2026-0003.png", "carpeta": "boletas/2026-07", "estado": "PENDIENTE", "drive_file_id": None},
]

NOTIFICACIONES = [
    {"tipo": "STOCK_BAJO", "titulo": "Stock bajo: Arroz 1kg", "mensaje": "Quedan 3 unidades de Arroz 1kg en inventario.", "leida": False, "entidad_origen": "inventario", "entidad_id": "1"},
    {"tipo": "STOCK_BAJO", "titulo": "Stock bajo: Aceite 1L", "mensaje": "Quedan 2 unidades de Aceite 1L en inventario.", "leida": False, "entidad_origen": "inventario", "entidad_id": "2"},
    {"tipo": "STOCK_BAJO", "titulo": "Stock bajo: Leche 1L", "mensaje": "Quedan 1 unidades de Leche 1L en inventario.", "leida": True, "entidad_origen": "inventario", "entidad_id": "3"},
    {"tipo": "CIERRE_CAJA", "titulo": "Cierre de caja exitoso", "mensaje": "Turno #5 cerrado con total de $1,250.00.", "leida": False, "entidad_origen": "caja", "entidad_id": "5"},
    {"tipo": "CIERRE_CAJA", "titulo": "Cierre de caja pendiente", "mensaje": "Turno #4 pendiente de cierre desde hace 2 horas.", "leida": True, "entidad_origen": "caja", "entidad_id": "4"},
    {"tipo": "SISTEMA", "titulo": "Backup completado", "mensaje": "Respaldo automático de la base de datos completado exitosamente.", "leida": False, "entidad_origen": "sistema", "entidad_id": None},
    {"tipo": "SISTEMA", "titulo": "Actualización disponible", "mensaje": "Hay una nueva versión del sistema disponible para actualizar.", "leida": True, "entidad_origen": "sistema", "entidad_id": None},
    {"tipo": "SISTEMA", "titulo": "Mantenimiento programado", "mensaje": "El sistema estará en mantenimiento el domingo de 2:00 a 4:00 AM.", "leida": True, "entidad_origen": "sistema", "entidad_id": None},
]

RESPALDOS = [
    {"archivo_nombre": "tienda_sistema_20260710_030000.dump", "tamano_bytes": 2457600, "estado": "COMPLETADO", "dias_atras": 6},
    {"archivo_nombre": "tienda_sistema_20260713_030000.dump", "tamano_bytes": 2621440, "estado": "COMPLETADO", "dias_atras": 3},
    {"archivo_nombre": "tienda_sistema_20260716_030000.dump", "tamano_bytes": 0, "estado": "PENDIENTE", "dias_atras": 0},
]


async def seed_demo() -> None:
    async with SessionLocal() as db:
        # Limpiar datos de demo anteriores
        await db.execute(delete(ArchivoDriveModel))
        await db.execute(delete(NotificacionModel))
        await db.execute(delete(RespaldoModel))
        await db.execute(delete(BoletaModel))
        await db.flush()

        # Boletas
        boletas_creadas = []
        for b in BOLETAS:
            fila = BoletaModel(
                venta_id=b["venta_id"],
                numero=b["numero"],
                total=b["total"],
                emitida_en=HOY - timedelta(days=b["dias_atras"]),
            )
            db.add(fila)
            await db.flush()
            boletas_creadas.append(fila)

        # Archivos Drive
        for a in ARCHIVOS_DRIVE:
            db.add(ArchivoDriveModel(
                boleta_id=boletas_creadas[a["boleta_idx"]].id,
                archivo_nombre=a["archivo_nombre"],
                carpeta=a["carpeta"],
                estado=a["estado"],
                drive_file_id=a["drive_file_id"],
            ))

        # Notificaciones
        for n in NOTIFICACIONES:
            db.add(NotificacionModel(
                tipo=n["tipo"],
                titulo=n["titulo"],
                mensaje=n["mensaje"],
                leida=n["leida"],
                entidad_origen=n["entidad_origen"],
                entidad_id=n["entidad_id"],
            ))

        # Respaldos
        for r in RESPALDOS:
            db.add(RespaldoModel(
                archivo_nombre=r["archivo_nombre"],
                tamano_bytes=r["tamano_bytes"],
                estado=r["estado"],
                expira_en=HOY + timedelta(days=30),
            ))

        await db.commit()
        print(f"Seed Module D demo: {len(BOLETAS)} boletas, {len(ARCHIVOS_DRIVE)} archivos_drive, {len(NOTIFICACIONES)} notificaciones, {len(RESPALDOS)} respaldos.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo())
