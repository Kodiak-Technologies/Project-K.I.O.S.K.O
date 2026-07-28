# Bugfixes-Verify — Post-PR3b Verification Fixes

**Date**: 2026-07-19
**Branch**: `feature/modulo_b_catalogo`
**Change**: `modulo-b-bugfixes-verify`
**Mode**: Strict TDD

This document records the 3 defects caught by post-PR3b E2E verification of Módulo B against the shared `kiosko-test` Supabase DB, plus the surgical fixes applied. The change is a single-commit bugfix release: no DB migration, no schema changes, no frontend changes.

---

## Summary

| # | Layer | Defect | Symptom | Root Cause | Fix |
|---|-------|--------|---------|------------|-----|
| 1 | Production (infra adapter) | `PATCH /productos/{id}/precio` returns HTTP 500 | Pydantic `ValidationError: id Input should be a valid integer, input_value=None` | `sqlalchemy_producto_repository.actualizar_precio` built the `HistorialPrecio` domain entity via `_historial_a_entidad(hist)` **before** `await self._db.flush()`. At that point the SQLAlchemy model has no DB-assigned `id`, so the entity carried `id=None`. The strict `id: int` schema then failed. | Reorder: build the entity **after** `flush()` so the model has the real `id`. |
| 2 | Production (domain entity) | `POST /ingresos/{id}/aprobar` returns HTTP 500 | `asyncpg.exceptions.CheckViolationError: chk_solicitudes_revisado_consistente` | `SolicitudIngreso.aprobar()` and `.rechazar()` set `revisado_por` and `revisado_por_nombre` but **not** `revisado_en`. The DB CHECK constraint requires `revisado_en IS NOT NULL` for terminal states. | Set `self.revisado_en = datetime.now(timezone.utc)` inside both `aprobar()` and `rechazar()`. Fixes the latent twin in `rechazar()`. |
| 3 | Test code | `test_invariante_deuda_proveedor` fails with `145 != 245` | Test iterates a SQLAlchemy `ScalarResult` twice; the second iteration sees 0 rows. | `ScalarResult` is a one-shot iterable. The first `sum()` consumed the result set; the second saw no rows, so `total_pago=0` and the invariant `credito - pago == deuda_actual` broke. | Materialize with `.scalars().all()`; add a 3-pagos regression scenario to prove the test exercises the real invariant. |

---

## Detailed fix descriptions

### Bug #1 — PATCH /productos/{id}/precio returns 500

**Where**:
- `backend/app/modules/modulo_b_inventario/infrastructure/adapters/database/sqlalchemy_producto_repository.py` — `actualizar_precio` (formerly lines 327-368).
- `backend/app/modules/modulo_b_inventario/infrastructure/http/schemas.py` — `HistorialPrecioResponse.id: int` (strict, non-nullable).

**Before (buggy)**:

```python
hist = HistorialPrecioModel(producto_id=..., ...)
self._db.add(hist)
filas_historial.append(_historial_a_entidad(hist))   # entity.id = None
fila.precio = nuevo
# ... later ...
await self._db.flush()                               # DB assigns id, but entity already captured as None
```

**After (fixed)**:

```python
hist = HistorialPrecioModel(producto_id=..., ...)
self._db.add(hist)
fila.precio = nuevo
# ... later ...
await self._db.flush()                               # DB assigns id
filas_historial.append(_historial_a_entidad(hist))   # entity.id = <int>
```

The `_historial_a_entidad(hist)` factory invocation is moved to **after** `await self._db.flush()`. This matches the pattern already used in `sqlalchemy_pago_proveedor_repository.py:54-58` and `sqlalchemy_historial_precio_repository.py:48-51`, where `fila.id` is assigned to the entity after flush. No call-site changes; only the ordering of two lines per branch (venta, compra).

### Bug #2 — POST /ingresos/{id}/aprobar CHECK constraint violation

**Where**:
- `backend/app/modules/modulo_b_inventario/domain/entities.py` — `SolicitudIngreso.aprobar` (formerly lines 114-122) and `SolicitudIngreso.rechazar` (formerly lines 124-136).
- `backend/db/schema_modulo_b_completo.sql:104-108` — `chk_solicitudes_revisado_consistente` definition (CHECK constraint, not modified).

**Before (buggy)**:

```python
def aprobar(self, usuario_id: int, nombre: str) -> None:
    ...
    self.estado = EstadoSolicitud("Aprobada")
    self.revisado_por = usuario_id
    self.revisado_por_nombre = nombre
    # revisado_en NOT SET → CHECK violation on UPDATE
```

**After (fixed)**:

```python
def aprobar(self, usuario_id: int, nombre: str) -> None:
    ...
    self.estado = EstadoSolicitud("Aprobada")
    self.revisado_por = usuario_id
    self.revisado_por_nombre = nombre
    self.revisado_en = datetime.now(timezone.utc)
```

The `rechazar()` method had the same latent bug (uncovered because no E2E covered it) and gets the same fix. The CHECK constraint is a domain invariant (D-09: a reviewed request must have a review timestamp), so the entity is the right layer. The `datetime` import is extended to `from datetime import datetime, timezone`.

### Bug #3 — test_invariante_deuda_proveedor double-iterates ScalarResult

**Where**:
- `backend/tests/modulo_b_inventario/test_caminos_criticos.py` — `test_invariante_deuda_proveedor` (formerly lines 333-345).

**Before (buggy)**:

```python
pagos = (
    await db.execute(
        select(PagoProveedorModel).where(
            PagoProveedorModel.proveedor_id == pid,
            PagoProveedorModel.deleted_at.is_(None),
        )
    )
).scalars()
total_credito = sum(p.monto for p in pagos if p.tipo == "compra_credito")  # 1st iter
total_pago = sum(p.monto for p in pagos if p.tipo == "pago")              # 2nd iter: empty
```

**After (fixed)**:

```python
pagos = (
    await db.execute(
        select(PagoProveedorModel).where(
            PagoProveedorModel.proveedor_id == pid,
            PagoProveedorModel.deleted_at.is_(None),
        )
    )
).scalars().all()  # materializes the result set
total_credito = sum(p.monto for p in pagos if p.tipo == "compra_credito")
total_pago = sum(p.monto for p in pagos if p.tipo == "pago")
```

Plus a new regression scenario `test_invariante_deuda_proveedor_3_pagos` that registers 1 compra_credito + 3 pagos and asserts the invariant holds. This proves the test would have caught a real production bug if one were introduced.

---

## Files changed

| File | Action | Δ | Purpose |
|---|---|---|---|
| `backend/app/modules/modulo_b_inventario/domain/entities.py` | Modified | +4 / -1 | Bug #2 fix: set `revisado_en` in `aprobar()` and `rechazar()`; extend `datetime` import. |
| `backend/app/modules/modulo_b_inventario/infrastructure/adapters/database/sqlalchemy_producto_repository.py` | Modified | +4 / -4 | Bug #1 fix: move `_historial_a_entidad(hist)` calls after `flush()` in `actualizar_precio`. |
| `backend/tests/modulo_b_inventario/test_caminos_criticos.py` | Modified | +25 / -2 | Bug #3 fix: materialize `pagos` with `.all()`; add 3-pagos regression scenario. |
| `backend/tests/modulo_b_inventario/test_unit_aprobar_ingreso.py` | Created | +90 | Strict TDD unit tests for `SolicitudIngreso.aprobar/rechazar` + use case persistence. |
| `backend/tests/modulo_b_inventario/test_unit_cambiar_precio.py` | Created | +80 | Strict TDD unit tests for `CambiarPrecioResponse` shape and `cambiar_precio` use case response integrity. |
| `docs/Cambios-Brayan/2026-07-19-bugfixes-verify.md` | Created | +170 | This file (project hard rule: document in Cambios-Brayan/). |

**Estimated total**: ~+207 / -7 = ~207 lines. Under the 400-line PR review budget.

---

## Strict TDD evidence

For each production-code fix, the unit test was written first and was confirmed to FAIL on the unmodified code:

- **Bug #2**: `test_unit_aprobar_ingreso.py` (3 tests) — wrote first; failed because `revisado_en` was `None` after `aprobar()`/`rechazar()`. After entities.py fix, all 3 pass.
- **Bug #1**: `test_unit_cambiar_precio.py` (2 tests) — wrote first; failed because the buggy adapter's entity carried `id=None`. After repository fix, both pass.
- **Bug #3**: The test fix IS the production of value; the modified `test_invariante_deuda_proveedor` was failing before the fix, and passes after. New `test_invariante_deuda_proveedor_3_pagos` adds the regression guard.

---

## E2E regression coverage

After the fixes, these E2E tests pass (all against the shared `kiosko-test` Supabase DB):

- `test_defensa_en_profundidad_admin_vs_cajero` — covers the PATCH /productos/{id}/precio happy path and the 9 permission matrix cells. After Bug #1 fix, the ADMIN happy path now returns 200 with a real `id` in `filas_historial`.
- `test_concurrencia_aprobacion_solicitud` — covers POST /ingresos/{id}/aprobar (Bug #2). After fix, the first call returns 200 and `revisado_en` is populated; the second concurrent call returns 409.
- `test_invariante_deuda_proveedor` (modified) + `test_invariante_deuda_proveedor_3_pagos` (new) — covers the deuda invariant (Bug #3). After fix, both iterations see the real persisted rows.

---

## Rollback

A single `git revert <commit-hash>` restores all 6 files to pre-fix state. No DB migration, so no schema rollback needed. The 3 affected E2E tests will fail again — that is the safe revert signal.

---

## Risks

- **Bug #1**: The reorder assumes the use case doesn't depend on `fila.id` being `None` pre-flush. Confirmed via the design and the use case code (`cambiar_precio_usecase.py` only consumes the returned tuple after the call returns; it does not inspect entities before).
- **Bug #2**: Pre-existing rows in `solicitudes_ingreso` with `estado IN ('Aprobada','Rechazada') AND revisado_en IS NULL` are impossible to write under the CHECK constraint, so the fix doesn't break existing data. Defensive pre-apply query confirmed zero such rows in the shared DB.
- **Bug #3**: The fix is purely test-side; production code is correct. If the invariant still fails after `.all()`, the next investigation target would be `_pagos.crear()` or `pago_proveedor_repository.crear()`. (Confirmed clean during explore #709.)
- **Environmental**: The shared Supabase `kiosko-test` is shared with modulo D. Existing tests use `secrets.token_hex(4)` to avoid collisions; no new risk introduced.
