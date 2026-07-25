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
5. Module D guarda la boleta en `boletas_clientes` con `url_pdf` temporal (PNG local) y `cliente_nombre`

### Flujos alternativos
- **3a.** Si la venta no existe → se registra error y se aborta
- **4a.** Si falla la generación del PNG → se guarda la boleta con `url_pdf = null` y se notifica el error

### Criterios de aceptación
- La boleta tiene un correlativo único formato `B001-NNNNNN`
- El PNG contiene: logo del negocio, nombre, número de boleta, fecha, detalle de productos, total, método de pago
- El `total` de la boleta coincide con el total de la venta
- `cliente_nombre` se guarda con el nombre del cliente (default: "Cliente 1" si no se proporciona)

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
2. El frontend llama a `GET /boletas?desde=&hasta=&cliente=`
3. El backend retorna la lista de boletas del período filtrada por cliente (opcional)
4. El usuario puede ver el correlativo, cliente, total, fecha y enlace a Drive

### Flujos alternativos
- **2a.** Si no hay boletas en el período → se retorna lista vacía `[]`
- **2b.** Si `url_pdf` es null → el frontend muestra "No disponible"

### Criterios de aceptación
- El endpoint requiere autenticación
- Las boletas se ordenan por fecha de emisión (más reciente primero)
- Se puede filtrar por rango de fechas y por nombre de cliente

---

## CU-D04: Generar Reporte de Ventas

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D06 |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el resumen de ventas con egresos y desglose por método de pago |

### Flujo principal
1. El Admin accede a la pantalla de reportes
2. El frontend llama a `GET /reportes/resumen?desde=&hasta=`
3. Module D consulta las ventas del período vía `VentaDataProviderPort`
4. Module D consulta egresos del período vía `EgresosDataProviderPort`
5. Module D consulta desglose por método de pago vía `MetodoPagoProviderPort`
6. Module D calcula: total_vendido, total_egresos, numero_ventas, ticket_promedio
7. Module D calcula top_productos (ranking por unidades y monto)
8. Module D retorna `ResumenReporte` con `total_egresos` y `metodos_pago`

### Flujos alternativos
- **3a.** Si no hay ventas en el período → se retorna todo en ceros
- **4a.** Si hay empate en top_productos → se ordena por monto descendente

### Criterios de aceptación
- Solo usuarios con rol ADMIN y permiso `reportes.ver` pueden acceder
- El ticket_promedio = total_vendido / numero_ventas
- Los top_productos incluyen nombre, cantidad y total por producto
- `total_egresos` incluye compras de mercadería y gastos operativos (RF-12)
- `metodos_pago` incluye desglose por EFECTIVO, YAPE, PLIN, TARJETA (RF-12)

---

## CU-D05: Generar Reporte de Más Vendidos / Menor Rotación

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D07, RF-14 |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el ranking de productos |

### Flujo principal
1. El Admin selecciona "Más vendidos" o "Menor rotación" en reportes
2. El frontend llama a `GET /reportes/mas-vendidos?orden=mayor|menor&desde=&hasta=`
3. Module D consulta el detalle de ventas del período
4. Module D calcula ranking por unidades vendidas y por monto
5. Module D retorna el ranking según el orden solicitado

### Flujos alternativos
- **4a.** Si se filtra por categoría → solo se incluyen productos de esa categoría
- **4b.** Si `orden=menor` → se muestra la lista invertida (menor rotación primero)

### Criterios de aceptación
- El ranking incluye: nombre del producto, cantidad total vendida, monto total
- Se puede ordenar por `mayor` (default) o `menor` rotación
- El endpoint es `GET /reportes/mas-vendidos` (separado del resumen)

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
- El endpoint `POST /notificaciones` permite crear notificaciones con envío automático por canales activos

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

## CU-D09: Consultar/Actualizar Configuración de Notificaciones

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D10 |
| **Precondiciones** | El usuario tiene rol ADMIN |
| **Postcondiciones** | La configuración de notificaciones está actualizada |

### Flujo principal
1. El Admin accede a la configuración de notificaciones
2. El frontend llama a `GET /notificaciones/config`
3. El backend retorna la configuración actual (canales activos, nivel de detalle, chat_id, correo)
4. El Admin modifica los campos y hace clic en "Guardar"
5. El frontend llama a `PUT /notificaciones/config` con los campos actualizados
6. El backend actualiza `config_notificaciones`

### Flujos alternativos
- **5a.** Si falta algún campo requerido → se retorna error 422

### Criterios de aceptación
- Solo ADMIN puede ver y editar la configuración
- GET retorna la configuración actual
- PUT actualiza los campos: `canal_telegram_activo`, `canal_correo_activo`, `nivel_detalle`, `telegram_chat_id`, `correo_destino`

---

## CU-D10: Generar Respaldo de BD

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

## CU-D11: Reintentar Subidas Pendientes

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (cron) |
| **HU** | HU-D04, RNF-01 |
| **Precondiciones** | Hay archivos con estado `PENDIENTE` o `FALLIDO` |
| **Postcondiciones** | Los archivos se reintantan subir a Google Drive |

### Flujo principal
1. El cron se activa cada 5 minutos
2. Module D consulta archivos con estado `PENDIENTE` o `FALLIDO` y menos de 3 intentos
3. Module D reintenta subir cada archivo a Google Drive
4. Si tiene éxito → estado `SUBIDO`; si falla → incrementa `intentos`

### Criterios de aceptación
- Máximo 3 reintentos por archivo
- Backoff exponencial entre reintentos
- Si alcanza el máximo, el archivo queda en estado `FALLIDO`

---

## CU-D12: Purgar Notificaciones Antiguas

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (cron) |
| **HU** | RNF-14 |
| **Precondiciones** | Hay notificaciones con más de 30 días |
| **Postcondiciones** | Las notificaciones antiguas se eliminan |

### Flujo principal
1. El cron se ejecuta después del backup diario
2. Se eliminan notificaciones con `created_at` mayor a 30 días

### Criterios de aceptación
- No se eliminan notificaciones de menos de 30 días
- El script es idempotente (ejecutarlo varias veces no causa errores)

---

## CU-D13: Autorizar Google Drive (OAuth)

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D02, HU-D04 |
| **Precondiciones** | El usuario tiene rol ADMIN |
| **Postcondiciones** | Google Drive está autorizado y los tokens se guardan en `oauth_tokens` |

### Flujo principal
1. El Admin ejecuta `GET /drive/auth-url` para obtener la URL de autorización
2. El frontend redirige al usuario a la URL de Google
3. El usuario autoriza la app en Google
4. Google redirige a `GET /drive/callback?code=CODE`
5. El backend intercambia el code por `access_token` + `refresh_token`
6. Los tokens se guardan en la tabla `oauth_tokens`
7. A partir de este momento, `POST /boletas/{id}/subir-drive` funciona

### Flujos alternativos
- **3a.** Si el usuario rechaza la autorización → se retorna error
- **5a.** Si el code es inválido → se retorna error 400
- **5b.** Si ya existe un token → se actualiza (re-autorización)

### Criterios de aceptación
- Solo usuarios con rol ADMIN pueden autorizar
- El `access_token` se renueva automáticamente cuando expira
- El `refresh_token` persiste indefinitely (a menos que el usuario lo revoque en Google)
- Se puede verificar el estado con `GET /drive/status`

---

## CU-D14: Descargar Boleta PNG

| Campo | Valor |
|-------|-------|
| **Actor** | Admin / Cajero |
| **HU** | HU-D03 |
| **Precondiciones** | El usuario está autenticado y la boleta existe |
| **Postcondiciones** | Se descarga el archivo PNG de la boleta |

### Flujo principal
1. El usuario hace clic en "Descargar" en la lista de boletas
2. El frontend llama a `GET /boletas/{id}/png`
3. El backend genera el PNG de la boleta (si no existe en Drive) y lo retorna como StreamingResponse
4. El frontend descarga el archivo con nombre descriptivo

### Criterios de aceptación
- El endpoint requiere autenticación
- El archivo se descarga con nombre `BOL-{numero}_{fecha}.png`
- El Content-Type es `image/png`

---

## CU-D15: Crear Notificación (API)

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema |
| **HU** | HU-D09, HU-D10 |
| **Precondiciones** | Hay un evento que notificar |
| **Postcondiciones** | La notificación se crea y se envía por canales activos |

### Flujo principal
1. Un módulo o servicio llama a `POST /notificaciones`
2. Se envía la notificación por Telegram (si `canal_telegram_activo`)
3. Se registra en `notificaciones`

### Criterios de aceptación
- Body: `{ tipo, titulo, mensaje, entidad_origen?, entidad_id? }`
- `tipo` ∈ `STOCK_BAJO | CIERRE_CAJA | SOLICITUD_INGRESO | SISTEMA`
- La notificación se guarda independientemente de si el envío falla

---

## CU-D16: Consultar Menor Rotación

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **HU** | HU-D07, RF-14 |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el ranking de menor rotación |

### Flujo principal
1. El Admin selecciona "Menor rotación" en reportes
2. El frontend llama a `GET /reportes/mas-vendidos?orden=menor`
3. Module D retorna la lista de productos ordenados por menor cantidad vendida

### Criterios de aceptación
- El mismo endpoint que "Más vendidos" con parámetro `orden=menor`
- Se muestra como parte del mismo reporte de productos

---

## Resumen de casos de uso

| CU | Nombre | Actor | HU | Puntos |
|----|--------|-------|----|---------|
| CU-D01 | Generar Boleta PNG | Sistema | HU-D01 | — |
| CU-D02 | Subir Boleta a Drive | Sistema | HU-D02, HU-D04 | — |
| CU-D03 | Consultar Boletas | Admin/Cajero | HU-D03 | — |
| CU-D04 | Generar Reporte Ventas | Admin | HU-D06 | — |
| CU-D05 | Generar Reporte Más/Menor | Admin | HU-D07, RF-14 | — |
| CU-D06 | Exportar a Excel | Admin | HU-D08 | — |
| CU-D07 | Enviar Notificación | Sistema | HU-D09, HU-D10 | — |
| CU-D08 | Consultar Notificaciones | Admin/Cajero | HU-D09 | — |
| CU-D09 | Config Notificaciones | Admin | HU-D10 | — |
| CU-D10 | Generar Respaldo | Admin/Cron | HU-D12 | — |
| CU-D11 | Reintentar Subidas | Cron | HU-D04, RNF-01 | — |
| CU-D12 | Purgar Notificaciones | Cron | RNF-14 | — |
| CU-D13 | Autorizar Google Drive | Admin | HU-D02, HU-D04 | — |
| CU-D14 | Descargar Boleta PNG | Admin/Cajero | HU-D03 | — |
| CU-D15 | Crear Notificación API | Sistema | HU-D09, HU-D10 | — |
| CU-D16 | Consultar Menor Rotación | Admin | HU-D07, RF-14 | — |
