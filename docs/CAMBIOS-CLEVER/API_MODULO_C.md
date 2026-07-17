# API del Módulo C + Guía de integración · Clever

Base URL local: `http://localhost:8000` · Swagger interactivo: `/docs`
Autenticación: header `Authorization: Bearer <access_token>` (Módulo A).
Errores: `{"detail": "mensaje en español"}` con 401/403/404/409/422.
Montos como números (2 decimales), fechas ISO 8601 (UTC).

> El schema DDL de las tablas es `backend/db/schema_modulo_c.sql` (SOL-03-C) y se aplica con
> `python -m scripts.aplicar_schema` (la BD compartida tiene una línea de migraciones de otra
> rama, por eso no se usa `alembic upgrade` ahí; las migraciones 0003–0009 existen igual para
> entornos limpios).

## 1. Caja (`/caja`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/caja/turno-actual` | autenticado | Turno ABIERTO o `null` |
| POST | `/caja/abrir` | `caja.abrir_turno` | `{monto_inicial}` → 201 turno. 409 si ya hay uno abierto |
| GET | `/caja/resumen` | autenticado | Sugerencia de cierre del turno abierto (RF-17) |
| POST | `/caja/cerrar` | `caja.cerrar_turno` | `{monto_final, comentario?}` → turno + arqueo. 422 si difiere de la sugerencia sin comentario |
| GET | `/caja/turnos?limite=30` | autenticado | Historial (visible para TODOS: cambio de turno) con arqueo |
| GET | `/caja/turnos/{id}/movimientos` | autenticado | RASTRO del turno: ventas, reversos y abonos (modal del ADMIN) |

Forma del turno: `{id, abierto_por, monto_inicial, monto_final, abierto_en, cerrado_en, estado, cerrado_por, arqueo}`
con `arqueo = {efectivo_esperado, efectivo_contado, diferencia, comentario, total_vendido, totales_por_metodo} | null`.

`GET /caja/resumen` →
```json
{ "turno": {...}, "efectivo_esperado": 135.5,
  "desglose": { "monto_inicial": 100.0, "ventas_efectivo": 55.5,
                "abonos_efectivo": 20.0, "devoluciones_efectivo": 40.0 },
  "totales_por_metodo": { "EFECTIVO": 55.5, "YAPE": 38.5, "FIADO": 37.0 },
  "total_vendido": 131.0, "numero_ventas": 6 }
```

## 2. Ventas (`/ventas`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| POST | `/ventas` | `ventas.registrar` | Registrar venta (descuenta stock atómico; 409 sin turno o sin stock) |
| GET | `/ventas?desde=&hasta=&turno_id=` | autenticado | Historial con detalles y pagos |
| POST | `/ventas/{id}/anular` | `ventas.anular` | `{motivo}` → reverso TOTAL: repone stock, ajusta caja, deja rastro |
| POST | `/ventas/{id}/devolver` | `ventas.devolver` | `{items: [{detalle_id, cantidad}], motivo}` → devolución parcial |

Cuerpo de `POST /ventas` (el contrato original `{items, metodo_pago}` sigue funcionando):
```json
{ "items": [{ "producto_id": 1, "cantidad": 2 }],
  "pagos": [{ "metodo": "EFECTIVO", "monto": 17.0, "monto_recibido": 20.0 },
             { "metodo": "YAPE", "monto": 20.0 }],
  "cliente_id": null,
  "client_uuid": "uuid-del-pos", "registrada_offline": false, "vendida_en": null }
```
- `pagos`: 1 = pago simple (puede omitir `monto`: cubre el total); >1 = MIXTO, la suma debe cuadrar EXACTO (422).
- `monto_recibido` (solo efectivo) → el backend calcula `vuelto`.
- FIADO: un único pago `{"metodo": "FIADO"}` + `cliente_id` obligatorio (422/409 si supera el límite de crédito).
- `client_uuid` (HU-C10): idempotencia — reintentar con el mismo uuid devuelve la venta ya creada, no duplica.

Respuesta: `{id, items:[{id, producto_id, nombre, precio_unitario, cantidad, cantidad_devuelta}], total,
metodo_pago, pagos:[{metodo, monto, es_efectivo, monto_recibido, vuelto}], vuelto, vendedor, cliente_id,
anulada, estado, turno_id, registrada_offline, vendida_en, created_at}`.
`estado` ∈ `COMPLETADA | ANULADA | DEVUELTA_PARCIAL`.

## 3. Métodos de pago (`/metodos-pago`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/metodos-pago?todos=false` | autenticado | Catálogo (activos; `todos=true` incluye desactivados) |
| POST | `/metodos-pago` | `metodos_pago.gestionar` | `{codigo, nombre, es_efectivo}` → 201 |
| PATCH | `/metodos-pago/{id}` | `metodos_pago.gestionar` | `{nombre?, activo?}` (EFECTIVO y FIADO no se desactivan) |

`es_efectivo = true` marca dinero FÍSICO: es lo único que cuenta para el arqueo (RF-17).

## 4. Clientes y fiados (`/clientes`, `/fiados`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/clientes?q=` | autenticado | Clientes activos (busca por nombre/alias) |
| POST | `/clientes` | `clientes.gestionar` | `{nombre, alias?, telefono?}` → 201 |
| PATCH | `/clientes/{id}` | `clientes.gestionar` | Datos básicos y `activo` |
| PATCH | `/clientes/{id}/limite-credito` | `clientes.limite_credito` (ADMIN) | `{limite_credito}` (0 = sin límite) |
| GET | `/fiados?cliente_id=&pendientes=true` | autenticado | Deudas (el frontend agrupa por cliente) |
| GET | `/fiados/{id}/abonos` | autenticado | Historial de abonos del fiado |
| POST | `/fiados/{id}/abonos` | `fiados.abonar` | `{monto, metodo}` → el dinero entra a la caja del turno abierto |

Forma del fiado: `{id, venta_id, cliente_id, cliente, monto_total, saldo_pendiente, estado, created_at}`
con `estado ∈ PENDIENTE | PAGADO | ANULADO`.

## 5. Permisos que el Módulo C agregó al seed

`ventas.devolver`, `metodos_pago.gestionar`, `clientes.gestionar`, `clientes.limite_credito`,
`fiados.abonar` — y `ventas.anular` pasó a estar disponible para CAJERO (HU-C08: el reverso lo
hace el cajero y el CONTROL es el rastro; la dueña puede quitárselo sin redeploy desde
`PUT /roles/{id}/permisos`). Avisado a Matías según su guía.

## 6. Notas de integración (para Brayan y Fabrizio)

- **Brayan (B):** Ventas consume la tabla `productos` SOLO vía el puerto `ProductoStockPort`
  (adaptador `sqlalchemy_stock_adapter.py`, misma transacción que la venta por RNF-03 —
  decisión documentada en el propio adaptador). Contrato usado: columnas
  `id, codigo, nombre, precio, stock, activo, deleted_at`. El descuento es
  `UPDATE ... SET stock = stock - n WHERE stock >= n` (nunca negativo). Mientras entregas tu
  módulo, dejé una implementación mínima de `/productos` y `/categorias` marcada como temporal.
- **Fabrizio (D):** cada venta confirmada está en `ventas` + `detalles_venta` + `pagos_venta`
  (todo con snapshots) — de ahí sale tu boleta PNG (RF-21). `GET /ventas?turno_id=` te da lo
  del día; las anuladas tienen `estado = 'ANULADA'` (marca la boleta como anulada). La BD
  compartida tenía placeholders tuyos de `ventas/detalles_venta/turnos_caja`: mi schema los
  reemplazó por las definitivas (tus tablas de boletas no se tocaron).
