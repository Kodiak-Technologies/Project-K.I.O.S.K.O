# Migración 0002 — Ingreso de mercadería

Equivalente SQL de `alembic/versions/0002_ingreso_producto_nuevo.py`, para
ejecutar a mano desde un editor SQL.

**Si puedes correr `alembic upgrade head` desde `backend/`, haz eso**: es lo
mismo, y además registra la versión (te ahorra el paso 3 de aquí abajo).

## Qué cambia

| Tabla | Cómo la afecta |
|---|---|
| `detalle_solicitud` | `precio_compra_unitario` → `precio_compra_total` (y se convierten los datos), `producto_id` pasa a nullable, 4 columnas nuevas, 2 CHECKs, índice parcial |
| `configuracion_negocio` | Columna nueva `margen_ganancia_default` |

No se borra ninguna fila ni ninguna columna con información. El único dato
existente que se modifica es el precio, multiplicado por `cantidad` para
convertirlo de unitario a total de línea.

---

## Paso 1 — Estado actual

Si hubo intentos previos fallidos:

```sql
ROLLBACK;
```

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'detalle_solicitud'
ORDER BY ordinal_position;
```

- Aparece `precio_compra_unitario` → no se aplicó nada, seguí al paso 2.
- Aparece `precio_compra_total` → quedó a medias. **No corras el paso 2**: el
  `RENAME` va a fallar y abortar todo. Revisa qué columnas faltan y aplica solo
  esas.

---

## Paso 2 — La migración

Todo en una transacción: si algo falla, no queda nada a medias.

**El `UPDATE` no debe correrse dos veces**: multiplicaría los precios de nuevo.

```sql
BEGIN;

ALTER TABLE detalle_solicitud
  RENAME COLUMN precio_compra_unitario TO precio_compra_total;

UPDATE detalle_solicitud
  SET precio_compra_total = precio_compra_total * cantidad;

ALTER TABLE detalle_solicitud
  ALTER COLUMN producto_id DROP NOT NULL;

ALTER TABLE detalle_solicitud
  ADD COLUMN nuevo_codigo VARCHAR(60),
  ADD COLUMN nuevo_nombre VARCHAR(150),
  ADD COLUMN nuevo_categoria_id INTEGER,
  ADD COLUMN margen_ganancia NUMERIC(5,2);

ALTER TABLE detalle_solicitud
  ADD CONSTRAINT fk_detsol_nueva_categoria
  FOREIGN KEY (nuevo_categoria_id)
  REFERENCES categorias (id)
  ON DELETE RESTRICT;

ALTER TABLE detalle_solicitud
  ADD CONSTRAINT chk_detsol_margen_no_negativo
  CHECK (margen_ganancia IS NULL OR margen_ganancia >= 0);

ALTER TABLE detalle_solicitud
  ADD CONSTRAINT chk_detsol_producto_o_nuevo
  CHECK (
    producto_id IS NOT NULL
    OR (
      nuevo_codigo IS NOT NULL
      AND length(trim(nuevo_codigo)) > 0
      AND nuevo_nombre IS NOT NULL
      AND length(trim(nuevo_nombre)) > 0
    )
  );

DROP INDEX idx_detsol_producto;

CREATE INDEX idx_detsol_producto
  ON detalle_solicitud (producto_id)
  WHERE producto_id IS NOT NULL;

ALTER TABLE configuracion_negocio
  ADD COLUMN margen_ganancia_default NUMERIC(5,2) NOT NULL DEFAULT 20;

COMMIT;
```

---

## Paso 3 — Marcar la migración como aplicada

Sin esto, un `alembic upgrade head` futuro intenta reaplicarla y falla en el
`RENAME COLUMN`.

```bash
cd backend && alembic stamp 0002_ingreso_producto_nuevo
```

---

## Paso 4 — Verificar

```sql
SELECT id, cantidad, precio_compra_total,
       round(precio_compra_total / cantidad, 2) AS costo_unitario
FROM detalle_solicitud
ORDER BY id;
```

`precio_compra_total` tiene que coincidir con lo que dice cada boleta. Si la
tabla está vacía, no hay nada que revisar.

```sql
SELECT margen_ganancia_default FROM configuracion_negocio;
```

Debe devolver `20.00`.
