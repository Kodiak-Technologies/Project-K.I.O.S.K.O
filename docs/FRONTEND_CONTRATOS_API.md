# Contratos de API que el frontend espera de los módulos B, C y D

El frontend de los módulos B (inventario), C (ventas) y D (documentos) ya está implementado contra estos endpoints. Son el **contrato**: si tu backend los respeta (ruta, método, cuerpo y respuesta), tu pantalla funciona sin tocar React. La fuente de verdad en código son los `*.port.ts` y `types/index.ts` de cada módulo del frontend.

Notas generales:

- Todas las rutas requieren `Authorization: Bearer <access_token>` (el interceptor de axios lo agrega solo).
- Los errores se devuelven como en el módulo A: `{"detail": "mensaje legible"}` con el status HTTP que corresponda. Ese `detail` se muestra tal cual al usuario.
- Fechas en ISO 8601 (UTC). Montos como números (no strings).
- Mientras un endpoint no exista (404), el frontend muestra "Módulo aún no conectado" — no es un bug.

---

## Módulo B — Inventario (Brayan)

### `GET /productos?q=<busqueda>`
Lista de productos; `q` filtra por nombre o código (opcional).

```json
[{ "id": 1, "codigo": "7750100000000", "nombre": "Arroz 5kg",
   "categoria_id": 2, "categoria": "Abarrotes",
   "precio": 18.5, "stock": 12, "stock_minimo": 5, "activo": true }]
```

### `POST /productos` — crear (ADMIN, permiso `productos.crear`)
Cuerpo: `{ codigo, nombre, categoria_id | null, precio, stock_minimo }` → responde el producto creado.

### `PATCH /productos/{id}` — editar (ADMIN, permisos `productos.editar` / `precios.editar`)
Cuerpo: cualquier subconjunto de los campos de arriba, más `activo: boolean` → responde el producto actualizado.

### `GET /categorias` / `POST /categorias`
`[{ "id": 1, "nombre": "Abarrotes" }]` · Crear: `{ "nombre": "Abarrotes" }`.

### `GET /ingresos`
Ingresos de mercadería, del más reciente al más antiguo.

```json
[{ "id": 7, "producto_id": 1, "producto": "Arroz 5kg", "cantidad": 20,
   "estado": "PENDIENTE", "solicitado_por": "vendedor1",
   "motivo_rechazo": null, "created_at": "2026-07-12T15:30:00Z" }]
```

`estado` ∈ `PENDIENTE | APROBADO | RECHAZADO`.

### `POST /ingresos` (permiso `inventario.solicitar_ingreso`)
Cuerpo: `{ producto_id, cantidad }` → crea el ingreso en estado `PENDIENTE`. **No debe sumar stock.**

### `POST /ingresos/{id}/aprobar` (ADMIN, permiso `inventario.aprobar_ingreso`)
Suma el stock y pasa a `APROBADO`. Registrar en bitácora.

### `POST /ingresos/{id}/rechazar` (ADMIN)
Cuerpo: `{ motivo }` → pasa a `RECHAZADO` sin tocar stock. Registrar en bitácora.

---

## Módulo C — Ventas (Clever)

### `GET /caja/turno-actual`
El turno abierto del día, o `null` si no hay.

```json
{ "id": 3, "abierto_por": "vendedor1", "monto_inicial": 50.0,
  "monto_final": null, "abierto_en": "2026-07-12T08:00:00Z",
  "cerrado_en": null, "estado": "ABIERTO" }
```

### `POST /caja/abrir` (permiso `caja.abrir_turno`)
Cuerpo: `{ monto_inicial }` → responde el turno creado. Debe rechazar si ya hay uno abierto.

### `POST /caja/cerrar` (permiso `caja.cerrar_turno`)
Cuerpo: `{ monto_final }` → cierra el turno y registra en bitácora la diferencia contra lo esperado (inicial + ventas en efectivo).

### `POST /ventas` (permiso `ventas.registrar`)
Cuerpo: `{ "items": [{ "producto_id": 1, "cantidad": 2 }], "metodo_pago": "EFECTIVO" }`.
`metodo_pago` ∈ `EFECTIVO | YAPE | PLIN | TARJETA`. Debe descontar stock y rechazar si la caja está cerrada.

Respuesta (y elemento de `GET /ventas`):

```json
{ "id": 12, "items": [{ "producto_id": 1, "nombre": "Arroz 5kg",
    "precio_unitario": 18.5, "cantidad": 2 }],
  "total": 37.0, "metodo_pago": "EFECTIVO", "vendedor": "vendedor1",
  "anulada": false, "created_at": "2026-07-12T10:15:00Z" }
```

### `GET /ventas?desde=&hasta=`
Historial filtrable por fecha (ambos opcionales).

### `POST /ventas/{id}/anular` (ADMIN, permiso `ventas.anular`)
Cuerpo: `{ motivo }` → marca `anulada: true`, devuelve stock y registra en bitácora. Nunca borra la fila.

---

## Módulo D — Documentos (Fabrizio)

### `GET /boletas?desde=&hasta=`

```json
[{ "id": 5, "venta_id": 12, "numero": "B001-000012", "total": 37.0,
   "emitida_en": "2026-07-12T10:15:05Z",
   "url_pdf": "https://drive.google.com/..." }]
```

`url_pdf` puede ser `null` si el PDF aún no se generó (el frontend muestra "No disponible").

### `GET /reportes/resumen?desde=&hasta=` (ADMIN, permiso `reportes.ver`)

```json
{ "desde": "2026-07-01", "hasta": "2026-07-12",
  "total_vendido": 1240.5, "numero_ventas": 87, "ticket_promedio": 14.26,
  "top_productos": [{ "nombre": "Arroz 5kg", "cantidad": 40, "total": 740.0 }] }
```

### `GET /notificaciones`

```json
[{ "id": 1, "tipo": "STOCK_BAJO", "titulo": "Stock bajo: Arroz 5kg",
   "mensaje": "Quedan 3 unidades (mínimo: 5).", "leida": false,
   "created_at": "2026-07-12T09:00:00Z" }]
```

`tipo` ∈ `STOCK_BAJO | CIERRE_CAJA | SISTEMA`.

### `POST /notificaciones/{id}/leida`
Marca como leída. Responde 200 sin cuerpo (o con la notificación, da igual: el frontend recarga la lista).
