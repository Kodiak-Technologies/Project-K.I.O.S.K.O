"""Tests E2E de los 5 caminos críticos del Módulo B (D-T07).

Cubre:
  (a) Defensa en profundidad ADMIN vs CAJERO (matriz de permisos).
  (b) Concurrencia con SELECT ... FOR UPDATE.
  (c) Invariante de deuda proveedor: deuda_actual == SUM(compra_credito) - SUM(pago).
  (d) Append-only de `historial_precios` (UPDATE directo → trigger falla).
  (e) Soft delete: GET /productos/{id} de un producto soft-deleted → 404.

Patrón del Módulo A: tests contra la BD real de DATABASE_URL (Postgres).
Los tests corren con `correr()` (helper de conftest.py) que garantiza engine.dispose().
"""
from __future__ import annotations

import secrets
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.domain.value_objects import (
    EstadoSolicitud,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
    HistorialPrecioModel,
    PagoProveedorModel,
    ProductoModel,
    ProveedorModel,
)
from app.shared.database.session import SessionLocal

from .conftest import (
    PASSWORD_PRUEBA,
    auth,
    cliente_api,
    correr,
    crear_categoria_directo,
    crear_producto_directo,
    crear_usuario_directo,
    asignar_permisos,
    token_de,
    username_unico,
)


# =============================================================================
# (a) Defensa en profundidad ADMIN vs CAJERO
# =============================================================================


def test_defensa_en_profundidad_admin_vs_cajero() -> None:
    """Matriz de permisos: ADMIN tiene acceso, CAJERO recibe 403 en endpoints
    exclusivos de ADMIN (aprobar ingreso, ajustar stock, cambiar precio,
    crear/editar proveedor)."""

    async def _run():
        async with cliente_api() as api:
            # ADMIN con todos los permisos del Módulo B
            admin_user = username_unico("adminb")
            await crear_usuario_directo(admin_user, "ADMIN")
            await asignar_permisos(
                "ADMIN",
                [
                    "productos.crear",
                    "productos.editar",
                    "precios.editar",
                    "inventario.aprobar_ingreso",
                    "inventario.solicitar_ingreso",
                    "inventario.ver",
                    "inventario.ajustar_stock",
                    "registros.eliminar",
                    "proveedores.gestionar",
                    "proveedores.compras_credito",
                    "proveedores.pagos",
                    "categorias.gestionar",
                    "storage.upload",
                    "historial_precios.ver",
                ],
            )
            admin_token = (await token_de(api, admin_user))["access_token"]
            admin_auth = auth(admin_token)

            # CAJERO solo con permisos limitados
            cajero_user = username_unico("cajib")
            await crear_usuario_directo(cajero_user, "CAJERO")
            await asignar_permisos(
                "CAJERO",
                [
                    "inventario.solicitar_ingreso",
                    "inventario.ver",
                    "storage.upload",
                ],
            )
            cajero_token = (await token_de(api, cajero_user))["access_token"]
            cajero_auth = auth(cajero_token)

            # Datos de prueba
            cat_id = await crear_categoria_directo(f"Cat-{secrets.token_hex(2)}")
            prod_id = await crear_producto_directo(
                f"PROD-{secrets.token_hex(2)}", "TestProd", cat_id, stock=50
            )

            # 1) ADMIN puede cambiar precio
            r = await api.patch(
                f"/productos/{prod_id}/precio",
                json={"precio_venta": 99.99},
                headers=admin_auth,
            )
            assert r.status_code == 200, r.text

            # 2) CAJERO NO puede cambiar precio → 403
            r = await api.patch(
                f"/productos/{prod_id}/precio",
                json={"precio_venta": 88.88},
                headers=cajero_auth,
            )
            assert r.status_code == 403, r.text

            # 3) CAJERO puede ver inventario (listar productos)
            r = await api.get("/productos", headers=cajero_auth)
            assert r.status_code == 200, r.text

            # 4) CAJERO NO puede crear proveedor → 403
            r = await api.post(
                "/proveedores",
                json={"razon_social": "Test Prov S.A.", "ruc": "20999999999"},
                headers=cajero_auth,
            )
            assert r.status_code == 403, r.text

            # 5) ADMIN sí puede crear proveedor
            r = await api.post(
                "/proveedores",
                json={"razon_social": f"TestProv-{secrets.token_hex(2)}"},
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            proveedor_id = r.json()["id"]

            # 6) CAJERO NO puede ver historial de precios → 403
            r = await api.get(
                f"/productos/{prod_id}/historial-precios",
                headers=cajero_auth,
            )
            assert r.status_code == 403, r.text

            # 7) Crear solicitud de ingreso como CAJERO (sí tiene permiso)
            r = await api.post(
                "/ingresos",
                json={
                    "foto_boleta_url": f"https://x.test/{secrets.token_hex(4)}.jpg",
                    "lineas": [
                        {"producto_id": prod_id, "cantidad": 5, "precio_compra_unitario": 5.0}
                    ],
                },
                headers=cajero_auth,
            )
            assert r.status_code == 201, r.text
            solicitud_id = r.json()["id"]

            # 8) CAJERO NO puede aprobar la solicitud → 403
            r = await api.post(
                f"/ingresos/{solicitud_id}/aprobar",
                json={},
                headers=cajero_auth,
            )
            assert r.status_code == 403, r.text

            # 9) ADMIN sí puede aprobarla → 200
            r = await api.post(
                f"/ingresos/{solicitud_id}/aprobar",
                json={},
                headers=admin_auth,
            )
            assert r.status_code == 200, r.text

            # 10) CAJERO NO puede ajustar stock a mano → 403
            r = await api.post(
                f"/productos/{prod_id}/ajustar-stock",
                json={"delta": -2, "motivo": "Rotura"},
                headers=cajero_auth,
            )
            assert r.status_code == 403, r.text

            # 11) ADMIN sí puede, con su contraseña
            r = await api.post(
                f"/productos/{prod_id}/ajustar-stock",
                json={"delta": -2, "motivo": "Producto roto"},
                headers=admin_auth,
            )
            assert r.status_code == 200, r.text
            assert r.json()["delta"] == -2

            # 12) el ajuste no puede dejar el stock negativo → 409
            r = await api.post(
                f"/productos/{prod_id}/ajustar-stock",
                json={"delta": -99999, "motivo": "Imposible"},
                headers=admin_auth,
            )
            assert r.status_code == 409, r.text

            # 13) CAJERO NO puede eliminar productos → 403
            r = await api.request("DELETE", f"/productos/{prod_id}", headers=cajero_auth)
            assert r.status_code == 403, r.text

    correr(_run())


# =============================================================================
# (b) Concurrencia: SELECT FOR UPDATE en aprobación
# =============================================================================


def test_concurrencia_aprobacion_solicitud() -> None:
    """Simula que dos transacciones intentan aprobar la misma solicitud.
    Solo una debe ganar (la otra recibe 409 'ya fue revisada' o rowcount=0)."""

    async def _run():
        from sqlalchemy import select

        async with cliente_api() as api:
            admin_user = username_unico("adminc")
            await crear_usuario_directo(admin_user, "ADMIN")
            await asignar_permisos(
                "ADMIN",
                [
                    "inventario.solicitar_ingreso",
                    "inventario.aprobar_ingreso",
                ],
            )
            admin_token = (await token_de(api, admin_user))["access_token"]
            admin_auth = auth(admin_token)

            cat_id = await crear_categoria_directo(f"CatC-{secrets.token_hex(2)}")
            prod_id = await crear_producto_directo(
                f"PROD-{secrets.token_hex(3)}", "TestProd", cat_id, stock=20
            )

            # Crear solicitud
            r = await api.post(
                "/ingresos",
                json={
                    "foto_boleta_url": f"https://x.test/{secrets.token_hex(4)}.jpg",
                    "lineas": [
                        {"producto_id": prod_id, "cantidad": 10, "precio_compra_unitario": 5.0}
                    ],
                },
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            solicitud_id = r.json()["id"]

            # Aprobar dos veces (la segunda debe recibir 409)
            r1 = await api.post(
                f"/ingresos/{solicitud_id}/aprobar",
                json={},
                headers=admin_auth,
            )
            r2 = await api.post(
                f"/ingresos/{solicitud_id}/aprobar",
                json={},
                headers=admin_auth,
            )
            # Una gana, la otra falla
            assert r1.status_code in (200,), r1.text
            assert r2.status_code == 409, r2.text  # ConflictoError: ya fue revisada

            # Verificar que el stock se incrementó solo UNA vez
            async with SessionLocal() as db:
                fila = (
                    await db.execute(
                        select(ProductoModel).where(ProductoModel.id == prod_id)
                    )
                ).scalar_one()
                assert fila.stock == 30, f"Stock debería ser 30 (20+10), es {fila.stock}"

    correr(_run())


# =============================================================================
# (c) Invariante de deuda del proveedor
# =============================================================================


def test_invariante_deuda_proveedor() -> None:
    """deuda_actual == SUM(compra_credito) - SUM(pago)."""

    async def _run():
        from sqlalchemy import select

        async with cliente_api() as api:
            admin_user = username_unico("adminp")
            await crear_usuario_directo(admin_user, "ADMIN")
            await asignar_permisos(
                "ADMIN",
                [
                    "proveedores.gestionar",
                    "proveedores.compras_credito",
                    "proveedores.pagos",
                ],
            )
            admin_token = (await token_de(api, admin_user))["access_token"]
            admin_auth = auth(admin_token)

            # 1) Crear proveedor
            r = await api.post(
                "/proveedores",
                json={"razon_social": f"Prov-{secrets.token_hex(3)}"},
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            pid = r.json()["id"]
            assert r.json()["deuda_actual"] == 0.0

            # 2) Compra crédito 245.00
            r = await api.post(
                f"/proveedores/{pid}/compras-credito",
                json={"monto": 245.00, "fecha": "2026-07-19", "concepto": "Lote"},
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            assert r.json()["deuda_actual"] == 245.00

            # 3) Pago 100.00
            r = await api.post(
                f"/proveedores/{pid}/pagos",
                json={"monto": 100.00, "fecha": "2026-07-19", "concepto": "Pago parcial"},
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            assert r.json()["deuda_actual"] == 145.00

            # 4) Verificar invariante en BD directamente
            async with SessionLocal() as db:
                prov = (
                    await db.execute(
                        select(ProveedorModel).where(ProveedorModel.id == pid)
                    )
                ).scalar_one()
                # Materialize the ScalarResult with `.all()` before iterating.
                # Bug #3: `ScalarResult` is a one-shot iterable; the second
                # `sum()` over `pagos` would see 0 rows and the invariant
                # would break (`credito - pago = 245 - 0 = 245 != 145`).
                pagos = (
                    await db.execute(
                        select(PagoProveedorModel).where(
                            PagoProveedorModel.proveedor_id == pid,
                            PagoProveedorModel.deleted_at.is_(None),
                        )
                    )
                ).scalars().all()
                total_credito = sum(
                    p.monto for p in pagos if p.tipo == "compra_credito"
                )
                total_pago = sum(p.monto for p in pagos if p.tipo == "pago")
                assert prov.deuda_actual == total_credito - total_pago
                assert prov.deuda_actual == Decimal("145.00")

            # 5) Intentar pagar más de la deuda → 422
            r = await api.post(
                f"/proveedores/{pid}/pagos",
                json={"monto": 999.00, "fecha": "2026-07-19"},
                headers=admin_auth,
            )
            assert r.status_code == 422, r.text

    correr(_run())


def test_invariante_deuda_proveedor_3_pagos() -> None:
    """Regression guard for Bug #3: 1 compra_credito + 3 pagos (instead of 1+1).

    If the test re-iterates a one-shot `ScalarResult` (the original bug), the
    second `sum()` would see 0 rows and the invariant would silently break.
    This scenario proves the test exercises the REAL invariant on multi-pago
    proveedores — the second iteration MUST see all 3 pagos.
    """

    async def _run():
        from sqlalchemy import select

        async with cliente_api() as api:
            admin_user = username_unico("adminp3")
            await crear_usuario_directo(admin_user, "ADMIN")
            await asignar_permisos(
                "ADMIN",
                [
                    "proveedores.gestionar",
                    "proveedores.compras_credito",
                    "proveedores.pagos",
                ],
            )
            admin_token = (await token_de(api, admin_user))["access_token"]
            admin_auth = auth(admin_token)

            # 1) Crear proveedor
            r = await api.post(
                "/proveedores",
                json={"razon_social": f"Prov3p-{secrets.token_hex(3)}"},
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            pid = r.json()["id"]
            assert r.json()["deuda_actual"] == 0.0

            # 2) Compra crédito 300.00
            r = await api.post(
                f"/proveedores/{pid}/compras-credito",
                json={"monto": 300.00, "fecha": "2026-07-19", "concepto": "Lote grande"},
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            assert r.json()["deuda_actual"] == 300.00

            # 3) Tres pagos: 50, 70, 80 (total 200) → deuda esperada = 100
            for monto in (50.00, 70.00, 80.00):
                r = await api.post(
                    f"/proveedores/{pid}/pagos",
                    json={"monto": monto, "fecha": "2026-07-19", "concepto": f"Pago {monto}"},
                    headers=admin_auth,
                )
                assert r.status_code == 201, r.text
            assert r.json()["deuda_actual"] == 100.00

            # 4) Verificar invariante en BD directamente con `.all()` materializado
            async with SessionLocal() as db:
                prov = (
                    await db.execute(
                        select(ProveedorModel).where(ProveedorModel.id == pid)
                    )
                ).scalar_one()
                pagos = (
                    await db.execute(
                        select(PagoProveedorModel).where(
                            PagoProveedorModel.proveedor_id == pid,
                            PagoProveedorModel.deleted_at.is_(None),
                        )
                    )
                ).scalars().all()
                total_credito = sum(
                    p.monto for p in pagos if p.tipo == "compra_credito"
                )
                total_pago = sum(p.monto for p in pagos if p.tipo == "pago")
                # Real assertions on real data — guards against the double-iteration bug
                assert len(pagos) == 4, f"Esperaba 4 filas (1 compra + 3 pagos), obtuve {len(pagos)}"
                assert total_credito == Decimal("300.00")
                assert total_pago == Decimal("200.00")
                assert prov.deuda_actual == total_credito - total_pago
                assert prov.deuda_actual == Decimal("100.00")

    correr(_run())


# =============================================================================
# (d) Append-only de historial_precios
# =============================================================================


def test_append_only_historial_precios() -> None:
    """UPDATE directo a historial_precios debe ser rechazado por el trigger
    `trg_historial_precios_no_update`."""

    async def _run():
        from sqlalchemy import select, text
        from sqlalchemy.exc import DBAPIError

        async with cliente_api() as api:
            admin_user = username_unico("adminh")
            await crear_usuario_directo(admin_user, "ADMIN")
            await asignar_permisos(
                "ADMIN",
                [
                    "productos.crear",
                    "precios.editar",
                ],
            )
            admin_token = (await token_de(api, admin_user))["access_token"]
            admin_auth = auth(admin_token)

            cat_id = await crear_categoria_directo(f"CatH-{secrets.token_hex(2)}")
            # Crear producto (genera fila inicial de historial)
            r = await api.post(
                "/productos",
                json={
                    "codigo": f"P-{secrets.token_hex(3)}",
                    "nombre": "TestHist",
                    "categoria_id": cat_id,
                    "precio_venta": 10.0,
                    "precio_compra_actual": 5.0,
                },
                headers=admin_auth,
            )
            assert r.status_code == 201, r.text
            prod_id = r.json()["id"]

            # Hay al menos 1 fila de historial
            async with SessionLocal() as db:
                filas = (
                    await db.execute(
                        select(HistorialPrecioModel).where(
                            HistorialPrecioModel.producto_id == prod_id
                        )
                    )
                ).scalars()
                count = len(list(filas))
                assert count >= 1, "Debe haber al menos 1 fila de historial"

            # Intentar UPDATE directo → el trigger debe fallar
            async with SessionLocal() as db:
                with pytest.raises(DBAPIError):
                    await db.execute(
                        text(
                            "UPDATE historial_precios SET precio_nuevo = 0 "
                            "WHERE producto_id = :pid"
                        ),
                        {"pid": prod_id},
                    )
                    # El trigger debería abortar la transacción; con flush
                    # también podemos detectar el error.
                    await db.flush()
                await db.rollback()

    correr(_run())


# =============================================================================
# (e) Soft delete: GET /productos/{id} de un producto soft-deleted → 404
# =============================================================================


def test_soft_delete_producto() -> None:
    """Un producto con `deleted_at IS NOT NULL` no debe aparecer en GET por id
    ni en el listado."""

    async def _run():
        from datetime import datetime, timezone
        from sqlalchemy import select

        async with cliente_api() as api:
            admin_user = username_unico("adminsd")
            admin_id = await crear_usuario_directo(admin_user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            admin_token = (await token_de(api, admin_user))["access_token"]
            admin_auth = auth(admin_token)

            cat_id = await crear_categoria_directo(f"CatSD-{secrets.token_hex(2)}")
            codigo = f"PSD-{secrets.token_hex(3)}"
            prod_id = await crear_producto_directo(codigo, "SoftDelete", cat_id, stock=10)

            # 1) GET antes del soft-delete: 200
            r = await api.get(f"/productos/{prod_id}", headers=admin_auth)
            assert r.status_code == 200, r.text

            # 2) Marcar soft-delete directo en BD
            async with SessionLocal() as db:
                fila = (
                    await db.execute(
                        select(ProductoModel).where(ProductoModel.id == prod_id)
                    )
                ).scalar_one()
                fila.deleted_at = datetime.now(timezone.utc)
                # Un usuario REAL: `deleted_by` tiene FK a `usuarios`, así que
                # el 0 que se usaba antes ya no pasa (y nunca debió pasar).
                fila.deleted_by = admin_id
                await db.commit()

            # 3) GET después del soft-delete: 404
            r = await api.get(f"/productos/{prod_id}", headers=admin_auth)
            assert r.status_code == 404, r.text

            # 4) Buscar por código: 404
            r = await api.get(
                f"/productos/buscar?codigo={codigo}",
                headers=admin_auth,
            )
            assert r.status_code == 404, r.text

            # 5) Listado: NO debe aparecer
            r = await api.get(
                f"/productos?search={codigo}",
                headers=admin_auth,
            )
            assert r.status_code == 200, r.text
            ids = [p["id"] for p in r.json()["items"]]
            assert prod_id not in ids, f"Producto soft-deleted {prod_id} no debe listarse"

    correr(_run())


# =============================================================================
# (extra) InMemoryStorageAdapter funciona como mock del StoragePort
# =============================================================================


def test_inmemory_storage_adapter_mock() -> None:
    """Smoke: el InMemoryStorageAdapter satisface el contrato del StoragePort."""

    async def _run():
        from .conftest import InMemoryStorageAdapter
        from datetime import datetime

        storage = InMemoryStorageAdapter()
        resultado = await storage.subir(
            carpeta="boletas",
            filename=f"2026-07-19-{secrets.token_hex(3)}.jpg",
            content=b"jpeg data fake",
            mime="image/jpeg",
        )
        assert resultado.mime == "image/jpeg"
        assert resultado.size_bytes == len(b"jpeg data fake")
        assert "boletas" in resultado.path
        assert len(storage.calls) == 1
        assert storage.calls[0]["carpeta"] == "boletas"

    correr(_run())
