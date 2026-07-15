# Casos de Uso — Módulo D (Documentos)

**Módulo**: Documentos (Boletas/Drive), Reportes, Notificaciones e Infraestructura
**Responsable**: Fabrizio
**Total HU**: 12 | **Total puntos**: 82

---

## CU-D01: Generar Boleta PNG

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (automático) |
| **HU** | HU-D01 |
| **Precondiciones** | La venta está confirmada en Module C |
| **Postcondiciones** | La boleta existe en `boletas_clientes` con PNG generado |

### Flujo principal
1. Module C confirma una venta y notifica a Module D
2. Module D consulta los datos de la venta vía `VentaDataProviderPort`
3. Module D consulta la configuración del negocio (logo, nombre) vía `ConfiguracionProviderPort`
4. Module D genera imagen PNG con Pillow (logo, correlativo, detalle, total, método de pago, fecha)
5. Module D guarda la boleta en `boletas_clientes` con `url_pdf` temporal (PNG local)

### Flujos alternativos
- **3a.** Si la venta no existe → se registra error y se aborta
- **4a.** Si falla la generación del PNG → se guarda la boleta con `url_pdf = null` y se notifica el error

### Criterios de aceptación
- La boleta tiene un correlativo único formato `B001-NNNNNN`
- El PNG contiene: logo del negocio, nombre, número de boleta, fecha, detalle de productos, total, método de pago
- El `total` de la boleta coincide con el total de la venta

---

## CU-D02: Subir Boleta a Google Drive

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (automático, post-generación) |
| **HU** | HU-D02, HU-D04 |
| **Precondiciones** | La boleta fue generada (CU-D01) |
| **Postcondiciones** | El archivo está en Google Drive y `url_pdf` está actualizado |

### Flujo principal
1. Module D lee el PNG generado de la boleta
2. Module D sube el archivo a Google Drive vía `DriveStoragePort` en carpeta `boletas/YYYY/MM/`
3. Module D actualiza `url_pdf` en `boletas_clientes` con la URL de Drive
4. Module D registra el archivo en `archivos_drive` con estado `SUBIDO`

### Flujos alternativos
- **2a.** Si Drive no está configurado (variables vacías) → se omite la subida y se deja el PNG local
- **2b.** Si falla la subida → se registra en `archivos_drive` con estado `FALLIDO` y se reintenta después

### Criterios de aceptación
- El archivo se organiza en carpetas por periodo: `boletas/2026/07/`
- Se registra el `drive_file_id` de Google Drive
- Si falla, el estado queda `PENDIENTE` o `FALLIDO` (no se pierde)

---

## CU-D03: Consultar Boletas

| Campo | Valor |
|-------|-------|
| **Actor** | Admin / Cajero |
| **HU** | HU-D03 |
| **Precondiciones** | El usuario está autenticado |
| **Postcondiciones** | Se retorna la lista de boletas filtrada |

### Flujo principal
1. El usuario accede a la pantalla de boletas
2. El frontend llama a `GET /boletas?desde=&hasta=`
3. El backend retorna la lista de boletas del período
4. El usuario puede ver el correlativo, total, fecha y enlace a Drive

### Flujos alternativos
- **2a.** Si no hay boletas en el período → se retorna lista vacía `[]`
- **2b.** Si `url_pdf` es null → el frontend muestra "No disponible"

### Criterios de aceptación
- El endpoint requiere autenticación
- Las boletas se ordenan por fecha de emisión (más reciente primero)
- Se puede filtrar por rango de fechas

---

## CU-D04: Generar Reporte de Ventas

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D06 |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el resumen de ventas |

### Flujo principal
1. El Admin accede a la pantalla de reportes
2. El frontend llama a `GET /reportes/resumen?desde=&hasta=`
3. Module D consulta las ventas del período vía `VentaDataProviderPort`
4. Module D calcula: total_vendido, numero_ventas, ticket_promedio
5. Module D calcula top_productos (ranking por unidades y monto)
6. Module D retorna `ResumenReporte`

### Flujos alternativos
- **3a.** Si no hay ventas en el período → se retorna todo en ceros
- **4a.** Si hay empate en top_productos → se ordena por monto descendente

### Criterios de aceptación
- Solo usuarios con rol ADMIN y permiso `reportes.ver` pueden acceder
- El ticket_promedio = total_vendido / numero_ventas
- Los top_productos incluyen nombre, cantidad y total por producto

---

## CU-D05: Generar Reporte de Más Vendidos

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D07 |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el ranking de productos |

### Flujo principal
1. El Admin selecciona "Más vendidos" en reportes
2. El frontend llama a `GET /reportes/resumen?desde=&hasta=`
3. Module D consulta el detalle de ventas del período
4. Module D calcula ranking por unidades vendidas y por monto
5. Module D retorna el top de productos

### Flujos alternativos
- **4a.** Si se filtra por categoría → solo se incluyen productos de esa categoría

### Criterios de aceptación
- El ranking incluye: nombre del producto, cantidad total vendida, monto total
- Se puede ordenar por unidades o por monto

---

## CU-D06: Exportar Reporte a Excel

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D08 |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se descarga un archivo .xlsx |

### Flujo principal
1. El Admin hace clic en "Exportar"
2. El frontend llama a `GET /reportes/exportar?desde=&hasta=&tipo=resumen`
3. Module D genera el archivo Excel vía `ReporteGeneratorPort`
4. Module D retorna el archivo con `media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`

### Flujos alternativos
- **3a.** Si falla la generación → se retorna error 500

### Criterios de aceptación
- El Excel contiene cabecera (nombre negocio, rango de fechas) y detalle
- Se puede exportar tipo `resumen` o `mas_vendidos`
- El archivo se descarga con nombre descriptivo

---

## CU-D07: Enviar Notificación

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema → Admin |
| **HU** | HU-D09, HU-D10 |
| **Precondiciones** | Hay un evento que notificar (stock bajo, cierre de caja, solicitud de ingreso) |
| **Postcondiciones** | La notificación existe en `notificaciones` y se envió por los canales activos |

### Flujo principal
1. Module D (u otro módulo) detecta un evento notificable
2. Module D lee `config_notificaciones` para saber canales activos
3. Module D envía por cada canal activo vía `NotificacionSenderPort` (Telegram, correo)
4. Module D registra la notificación en `notificaciones`

### Flujos alternativos
- **2a.** Si no hay canales activos → solo se guarda en BD
- **3a.** Si falla el envío → la notificación se guarda igual con `leida = false`

### Criterios de aceptación
- La notificación tiene tipo, título, mensaje
- Se puede marcar como leída con `POST /notificaciones/{id}/leida`
- Las notificaciones expiran después de 30 días (se purgan con script)

---

## CU-D08: Consultar Notificaciones

| Campo | Valor |
|-------|-------|
| **Actor** | Admin / Cajero |
| **HU** | HU-D09 |
| **Precondiciones** | El usuario está autenticado |
| **Postcondiciones** | Se retorna la lista de notificaciones |

### Flujo principal
1. El usuario accede a la campana de notificaciones
2. El frontend llama a `GET /notificaciones`
3. El backend retorna la lista (no leídas primero)

### Flujos alternativos
- **3a.** Si no hay notificaciones → se retorna lista vacía `[]`

### Criterios de aceptación
- Las notificaciones no leídas aparecen primero
- El usuario puede marcar como leída con `POST /notificaciones/{id}/leida`
- El marcado como leída retorna 200

---

## CU-D09: Generar Respaldo de BD

| Campo | Valor |
|-------|-------|
| **Actor** | Admin / Sistema (cron) |
| **HU** | HU-D12 |
| **Precondiciones** | El usuario tiene permiso ADMIN |
| **Postcondiciones** | Existe un archivo .dump en `backups/` y registro en `respaldos` |

### Flujo principal
1. El Admin ejecuta "Generar respaldo" o el cron se activa a las 2:00 AM
2. Module D ejecuta `pg_dump` de `tienda_sistema`
3. Module D guarda el archivo con timestamp: `backups/tienda_sistema_YYYYMMDD_HHMMSS.dump`
4. Module D registra en `respaldos` con estado `COMPLETADO`

### Flujos alternativos
- **2a.** Si falla el pg_dump → se registra con estado `FALLIDO`
- **4a.** Si hay respaldos con más de 30 días → se eliminan automáticamente

### Criterios de aceptación
- El respaldo es un archivo .dump válido
- Se registra tamaño, fecha y estado
- Los respaldos expiran después de 30 días

---

## CU-D10: Purgar Notificaciones Antiguas

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (cron) |
| **HU** | RNF-14 |
| **Precondiciones** | Hay notificaciones con más de 30 días |
| **Postcondiciones** | Las notificaciones antiguas se eliminan |

### Flujo principal
1. El script `purgar_notificaciones.py` se ejecuta después del backup diario
2. Se eliminan notificaciones con `created_at` mayor a 30 días

### Criterios de aceptación
- No se eliminan notificaciones de menos de 30 días
- El script es idempotente (ejecutarlo varias veces no causa errores)

---

## Resumen de casos de uso

| CU | Nombre | Actor | HU | Puntos |
|----|--------|-------|----|---------|
| CU-D01 | Generar Boleta PNG | Sistema | HU-D01 | — |
| CU-D02 | Subir Boleta a Drive | Sistema | HU-D02, HU-D04 | — |
| CU-D03 | Consultar Boletas | Admin/Cajero | HU-D03 | — |
| CU-D04 | Generar Reporte Ventas | Admin | HU-D06 | — |
| CU-D05 | Generar Reporte Más Vendidos | Admin | HU-D07 | — |
| CU-D06 | Exportar a Excel | Admin | HU-D08 | — |
| CU-D07 | Enviar Notificación | Sistema | HU-D09, HU-D10 | — |
| CU-D08 | Consultar Notificaciones | Admin/Cajero | HU-D09 | — |
| CU-D09 | Generar Respaldo | Admin/Cron | HU-D12 | — |
| CU-D10 | Purgar Notificaciones | Cron | RNF-14 | — |
