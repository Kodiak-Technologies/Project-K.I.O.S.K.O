# Diagrama Entidad-Relación — Módulo C (Ventas, Caja y Punto de Venta) · Clever

Tablas del Módulo C en PostgreSQL (SOL-01-C). Todas las fechas son `TIMESTAMPTZ` y todos los
montos `NUMERIC(10,2)`. Nada se borra físicamente: las ventas se ANULAN con un reverso que
deja rastro, y los FK usan `ON DELETE RESTRICT` para que nadie con historial pueda desaparecer.
El script DDL de estas tablas es `backend/db/schema_modulo_c.sql` (SOL-03-C).

```mermaid
erDiagram
    USUARIOS ||--o{ TURNOS_CAJA : "abre/cierra"
    USUARIOS ||--o{ VENTAS : "vende"
    TURNOS_CAJA ||--o{ VENTAS : "agrupa (1 turno - N ventas)"
    TURNOS_CAJA ||--|| ARQUEOS : "se cierra con (1 a 1)"
    TURNOS_CAJA ||--o{ ANULACIONES : "registra reversos hechos en el turno"
    TURNOS_CAJA ||--o{ ABONOS : "recibe abonos cobrados en el turno"
    VENTAS ||--o{ DETALLES_VENTA : "contiene (1 venta - N lineas)"
    VENTAS ||--o{ PAGOS_VENTA : "se paga con (mixto = varios)"
    VENTAS ||--o{ ANULACIONES : "puede revertirse"
    VENTAS ||--o| FIADOS : "si es al fiado genera (1 a 1)"
    PRODUCTOS ||--o{ DETALLES_VENTA : "se vende en (FK al Modulo B)"
    METODOS_PAGO ||--o{ PAGOS_VENTA : "clasifica"
    METODOS_PAGO ||--o{ ABONOS : "clasifica"
    CLIENTES ||--o{ VENTAS : "compra (opcional)"
    CLIENTES ||--o{ FIADOS : "debe (1 cliente - N fiados)"
    FIADOS ||--o{ ABONOS : "se salda con"

    TURNOS_CAJA {
        bigint id PK
        bigint usuario_id FK "-> usuarios.id (RESTRICT), quien abrio"
        varchar abierto_por "snapshot del nombre"
        numeric monto_inicial "efectivo contado al abrir (HU-C06)"
        varchar estado "ABIERTO | CERRADO; indice parcial unico: solo 1 ABIERTO"
        timestamptz abierto_en
        timestamptz cerrado_en
        numeric monto_final "efectivo REAL contado al cierre"
        bigint usuario_cierre_id FK "puede cerrar otro cajero (cambio de turno)"
        varchar cerrado_por
    }

    ARQUEOS {
        bigint id PK
        bigint turno_id PK, FK "UNIQUE: un arqueo por turno (RF-17)"
        bigint usuario_id FK
        varchar cerrado_por
        numeric efectivo_esperado "sugerencia: inicial + ventas efectivo + abonos - devoluciones"
        numeric efectivo_contado
        numeric diferencia "contado - esperado; el descuadre queda registrado"
        text comentario "OBLIGATORIO si hay diferencia; lo revisa la administradora"
        numeric total_vendido
        jsonb totales_por_metodo "desglose informativo (digital no esta en caja)"
        timestamptz created_at
    }

    VENTAS {
        bigint id PK
        bigint turno_id FK "-> turnos_caja (sin turno abierto no hay venta)"
        bigint usuario_id FK
        varchar vendedor "snapshot"
        bigint cliente_id FK "obligatorio si es al fiado"
        numeric total
        varchar metodo_pago "resumen: EFECTIVO | YAPE | ... | MIXTO | FIADO"
        varchar estado "COMPLETADA | ANULADA | DEVUELTA_PARCIAL"
        text motivo_anulacion
        varchar client_uuid UK "idempotencia de la sincronizacion offline (HU-C10)"
        boolean registrada_offline
        timestamptz vendida_en "momento real de la venta (offline != created_at)"
        timestamptz created_at
    }

    DETALLES_VENTA {
        bigint id PK
        bigint venta_id FK
        bigint producto_id FK "-> productos.id (Modulo B, FK acordada)"
        varchar nombre "SNAPSHOT: cambiar el precio hoy no altera reportes (RF-18)"
        numeric precio_unitario "SNAPSHOT"
        int cantidad "CHECK > 0"
        int cantidad_devuelta "acumulado de devoluciones parciales"
    }

    METODOS_PAGO {
        int id PK
        varchar codigo UK "EFECTIVO | YAPE | PLIN | TARJETA | TRANSFERENCIA | FIADO | ..."
        varchar nombre
        boolean es_efectivo "TRUE = dinero fisico que cuenta para el arqueo"
        boolean activo "el ADMIN agrega/desactiva (RF-20); EFECTIVO y FIADO protegidos"
    }

    PAGOS_VENTA {
        bigint id PK
        bigint venta_id FK
        int metodo_pago_id FK
        varchar codigo_metodo "snapshot para el historial"
        boolean es_efectivo "snapshot"
        numeric monto "CHECK > 0; la suma de pagos cuadra EXACTO con el total"
        numeric monto_recibido "solo efectivo: para calcular el vuelto"
    }

    ANULACIONES {
        bigint id PK
        bigint venta_id FK "la venta original NUNCA se borra"
        bigint turno_id FK "turno donde OCURRE el reverso: ajusta ESA caja"
        varchar tipo "ANULACION | DEVOLUCION"
        bigint usuario_id FK
        varchar realizado_por "el rastro que ve la administradora"
        text motivo "obligatorio"
        numeric monto "valor de lo revertido"
        numeric efectivo_devuelto "cuanto salio fisicamente del cajon"
        jsonb items "[{producto_id, nombre, cantidad}]"
        timestamptz created_at
    }

    CLIENTES {
        bigint id PK
        varchar nombre "indice"
        varchar alias
        varchar telefono
        numeric limite_credito "0 = sin limite; solo lo fija el ADMIN (RF-28)"
        boolean activo
        timestamptz created_at
    }

    FIADOS {
        bigint id PK
        bigint venta_id PK, FK "UNIQUE: un fiado nace de UNA venta"
        bigint cliente_id FK
        numeric monto_total
        numeric saldo_pendiente "baja con cada abono"
        varchar estado "PENDIENTE | PAGADO | ANULADO"
        timestamptz created_at
    }

    ABONOS {
        bigint id PK
        bigint fiado_id FK
        bigint turno_id FK "si es efectivo, entra al arqueo de ESE turno"
        bigint usuario_id FK
        varchar registrado_por
        int metodo_pago_id FK
        varchar codigo_metodo "snapshot"
        boolean es_efectivo
        numeric monto "CHECK > 0; nunca mayor al saldo"
        timestamptz created_at
    }
```

## Decisiones de diseño

- **Índice parcial único `ux_turnos_caja_abierto`** (`WHERE estado = 'ABIERTO'`): la tienda tiene
  una sola caja física, así que la BD misma impide dos turnos abiertos a la vez.
- **Snapshots en `detalles_venta` y `pagos_venta`** (`nombre`, `precio_unitario`, `codigo_metodo`,
  `es_efectivo`): los reportes históricos no se alteran cuando el ADMIN cambia precios o renombra
  métodos de pago (RF-18).
- **Modelo entrada/salida de efectivo por turno (RF-17)**: el dinero *entra* con las ventas y
  abonos del turno y *sale* con los reversos hechos durante el turno (`anulaciones.turno_id` es el
  turno del reverso, no el de la venta). Así el arqueo cuadra aunque se anule hoy una venta de ayer.
- **`es_efectivo` en el catálogo de métodos**: separa el dinero físico del digital; el arqueo solo
  cuadra contra efectivo y lo digital se muestra aparte ("existe pero no está en el cajón").
- **La venta nunca se borra (RF-22)**: `estado` + tabla `anulaciones` como rastro inmutable de
  reversos con quién/cuándo/motivo/efectivo devuelto.
- **`fiados.venta_id UNIQUE` (RF-28)**: la deuda nace de una venta concreta; el fiado no ingresa
  dinero (no genera `pagos_venta` en efectivo) y los abonos sí lo hacen, en su propio turno.
- **`ventas.client_uuid UNIQUE` (RF-26)**: idempotencia de la sincronización offline — si el POS
  reintenta enviar la misma venta local dos veces, la segunda no duplica.
- **FK cruzada acordada con el Módulo B** (`detalles_venta.producto_id -> productos.id`): única
  dependencia física entre módulos, acordada según `ARQUITECTURA.md` §4; el código accede al stock
  solo a través del puerto `ProductoStockPort`.
