# Migración 0003 — Quitar el margen de ganancia del ingreso

Equivalente SQL de `alembic/versions/0003_quitar_margen_ganancia.py`, para
ejecutar a mano desde un editor SQL.

**Si puedes correr `alembic upgrade head` desde `backend/`, haz eso**: es lo
mismo, y además registra la versión (te ahorra el paso 2 de aquí abajo).

## Por qué

Aprobar un ingreso calculaba el precio de venta del producto que se daba de
alta: costo unitario + un margen (el de la línea, o el 20% por defecto del
negocio). El efecto era que una compra terminaba fijando el precio del catálogo
y, por lo tanto, el del punto de venta, sin que nadie lo decidiera.

Ahora el ingreso no toca precios de venta:

- El producto que se crea al aprobar nace en **S/ 0.00** y el precio se le pone
  a mano desde el catálogo.
- El precio de venta de un producto **que ya existe** no se modifica nunca.
- El precio de **compra** sí se sigue actualizando con lo que dice la boleta:
  es el dato real del ingreso y no afecta al punto de venta.

Las dos columnas que sostenían el cálculo quedan sin uso.

## Qué cambia

| Tabla | Cómo la afecta |
|---|---|
| `detalle_solicitud` | Se elimina `margen_ganancia` y su CHECK `chk_detsol_margen_no_negativo` |
| `configuracion_negocio` | Se elimina `margen_ganancia_default` |

Se pierden los márgenes cargados por línea en solicitudes pendientes. No afecta
a ninguna solicitud ya aprobada: el margen solo se leía en el momento de
aprobar.

---

## Paso 1 — Eliminar las columnas

```sql
ALTER TABLE detalle_solicitud
  DROP CONSTRAINT chk_detsol_margen_no_negativo;

ALTER TABLE detalle_solicitud
  DROP COLUMN margen_ganancia;

ALTER TABLE configuracion_negocio
  DROP COLUMN margen_ganancia_default;
```

---

## Paso 2 — Marcar la migración como aplicada

Sin esto, un `alembic upgrade head` futuro intenta reaplicarla y falla en el
`DROP CONSTRAINT`.

```bash
cd backend && alembic stamp 0003_quitar_margen_ganancia
```

---

## Paso 3 — Verificar

```sql
SELECT column_name
FROM information_schema.columns
WHERE (table_name = 'detalle_solicitud'    AND column_name = 'margen_ganancia')
   OR (table_name = 'configuracion_negocio' AND column_name = 'margen_ganancia_default');
```

No debe devolver ninguna fila.
