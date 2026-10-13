# Cambio 0004 — Fiados

**No hay que correr nada a mano.** El backend crea lo que falte al arrancar
(`app/modules/modulo_c_ventas/infrastructure/adapters/database/esquema_fiados.py`,
llamado desde el `lifespan` de `app/main.py`). Es idempotente: si ya existe, no
hace nada.

No usa Alembic por el mismo motivo que el módulo C: la BD compartida tiene un
`alembic_version` de otra rama que no existe en este repo.

## Qué crea

- `clientes_fiado`: la cuenta de cada cliente. `saldo` > 0 es crédito ya pagado a
  favor; < 0 es lo que debe. `limite_mensual` es el tope de lo que se le fía en
  el mes (no bloquea: pasarlo deja una notificación para la administradora).
- `movimientos_fiado`: el estado de cuenta, append-only. Tipos:
  - `CONSUMO`: venta fiada. Resta saldo y **no** entra a la caja.
  - `PAGO`: el cliente paga lo que debe. Suma saldo y entra a la caja del turno
    en que paga (`turno_id`, `entra_a_caja = TRUE`).
  - `ADELANTO`: crédito ya pagado (solo ADMIN). Suma saldo y entra a la caja.
  - `REVERSO`: anulación/devolución de una venta fiada. Primero baja la deuda.
- Una fila en `metodos_pago`: `FIADO`, **inactiva**. Inactiva a propósito: el
  catálogo normal (y cualquier front viejo) no la ofrece; el backend la usa solo
  cuando la venta trae `cliente_fiado_id`.

No modifica ni borra ninguna tabla ni fila existente.

## Efecto en la caja

- Efectivo esperado del cierre = inicial + ventas en efectivo + **pagos de fiado
  en efectivo del turno** − devoluciones en efectivo.
- Lo fiado aparece en el desglose por método como `FIADO`, pero no suma al
  total neto del turno.
