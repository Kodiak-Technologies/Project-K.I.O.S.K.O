# Casos de Uso — Modulo D (Documentos)

**Modulo**: Notas de Venta, Reportes, Notificaciones, Respaldos e Infraestructura
**Responsable**: Fabrizio

---

## CU-D01: Generar Nota de Venta PNG

| Campo | Valor |
|-------|-------|
| **Actor** | Admin / Cajero |
| **Precondiciones** | El usuario esta autenticado y existen ventas registradas |
| **Postcondiciones** | Se genera un PNG con el formato de nota de venta |

### Flujo principal
1. El usuario accede a la pantalla de Notas de Venta
2. El frontend llama a `GET /notas-venta?desde=&hasta=`
3. El usuario hace clic en "PNG" para descargar una nota individual
4. El frontend llama a `GET /notas-venta/{venta_id}/png`
5. El backend genera el PNG con Pillow (formato termico: encabezado, productos, total)
6. Se retorna como `StreamingResponse` con `image/png`

### Criterios de aceptacion
- Canvas de 5000px, recortado al tamano real del contenido
- Soporta cualquier cantidad de productos sin cortarse
- Contenido: logo/nombre del negocio, fecha, correlativo, productos, total, metodo de pago

---

## CU-D02: Descargar Notas de Venta (ZIP)

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El usuario tiene rol ADMIN |
| **Postcondiciones** | Se descarga un .zip con los PNGs de las notas |

### Flujo principal
1. El Admin selecciona rango de fechas y hace clic en "Descargar ZIP"
2. El frontend llama a `POST /notas-venta/descargar` con `{desde, hasta}`
3. El backend genera los PNGs de todas las ventas del rango
4. Si hay 1 venta: retorna el PNG directamente. Si hay varias: las empaqueta en .zip
5. Se retorna como `StreamingResponse`

### Criterios de aceptacion
- Si hay 1 sola venta, se descarga el PNG directo (sin zip)
- Si hay varias, se crea un `.zip` con todas las notas
- Nombre del archivo: `notas-venta.zip`

---

## CU-D03: Generar Reporte de Ventas

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el resumen de ventas con egresos y desglose por metodo de pago |

### Flujo principal
1. El Admin accede a la pantalla de reportes
2. El frontend llama a `GET /reportes/resumen?desde=&hasta=`
3. Module D consulta las ventas del periodo via `VentaDataProviderPort`
4. Module D consulta egresos del periodo via `EgresosDataProviderPort`
5. Module D consulta desglose por metodo de pago via `MetodoPagoProviderPort`
6. Module D calcula: total_vendido, total_egresos, numero_ventas, ticket_promedio
7. Module D calcula top_productos (ranking por unidades y monto)

### Criterios de aceptacion
- Solo usuarios con rol ADMIN y permiso `reportes.ver` pueden acceder
- ticket_promedio = total_vendido / numero_ventas
- Los top_productos incluyen nombre, cantidad y total por producto
- `total_egresos` incluye compras de mercaderia y gastos operativos
- `metodos_pago` incluye desglose por EFECTIVO, YAPE, PLIN, TARJETA

---

## CU-D04: Generar Reporte de Mas Vendidos / Menor Rotacion

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se retorna el ranking de productos |

### Flujo principal
1. El Admin selecciona "Mas vendidos" o "Menor rotacion" en reportes
2. El frontend llama a `GET /reportes/mas-vendidos?orden=mayor|menor&desde=&hasta=`
3. Module D calcula ranking por unidades vendidas y por monto
4. Module D retorna el ranking segun el orden solicitado

### Criterios de aceptacion
- El ranking incluye: nombre del producto, cantidad total vendida, monto total
- Se puede ordenar por `mayor` (default) o `menor` rotacion
- Endpoint separado del resumen

---

## CU-D05: Exportar Reporte a Excel

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El usuario tiene permiso `reportes.ver` |
| **Postcondiciones** | Se descarga un archivo .xlsx |

### Flujo principal
1. El Admin hace clic en "Exportar"
2. El frontend llama a `GET /reportes/exportar?desde=&hasta=&tipo=resumen`
3. Module D genera el archivo Excel via `ReporteGeneratorPort`
4. Module D retorna el archivo con `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### Criterios de aceptacion
- El Excel contiene cabecera (nombre negocio, rango de fechas) y detalle
- Se puede exportar tipo `resumen` o `mas_vendidos`
- El archivo se descarga con nombre descriptivo

---

## CU-D06: Enviar Notificacion (API)

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (otros modulos) |
| **Precondiciones** | Hay un evento que notificar |
| **Postcondiciones** | La notificacion existe en `notificaciones` y se envio por los canales activos |

### Flujo principal
1. Un modulo o servicio llama a `POST /notificaciones`
2. Si `usuario_id` es NULL (broadcast admin): se envia por Telegram y Correo (si estan activos)
3. Si `usuario_id` tiene valor (trabajador): solo se guarda en BD (solo sistema)
4. Se registra la notificacion en `notificaciones`

### Criterios de aceptacion
- Body: `{ tipo, titulo, mensaje, entidad_origen?, entidad_id?, usuario_id?, producto_id? }`
- `tipo` en `STOCK_BAJO | APERTURA_CAJA | CIERRE_CAJA | SOLICITUD_INGRESO | SISTEMA`
- La notificacion se guarda independientemente de si el envio falla
- Admin recibe via: sistema + Telegram + correo
- Trabajador recibe via: solo sistema

---

## CU-D07: Consultar Notificaciones

| Campo | Valor |
|-------|-------|
| **Actor** | Admin / Cajero |
| **Precondiciones** | El usuario esta autenticado |
| **Postcondiciones** | Se retorna la lista de notificaciones del usuario |

### Flujo principal
1. El usuario accede a la campana de notificaciones o a la pagina de notificaciones
2. El frontend llama a `GET /notificaciones`
3. El backend retorna las notificaciones del usuario (no leidas primero)
4. Al abrir la campana o entrar a la pagina, se marcan todas como leidas automaticamente

### Criterios de aceptacion
- Las notificaciones no leidas aparecen primero
- Se puede marcar individualmente con `POST /notificaciones/{id}/leida`
- Se pueden marcar todas con `POST /notificaciones/leer-todas`
- La campana muestra el contador de no leidas (maximo "9+")
- Al abrir la campana, se muestran las 6 no leidas mas recientes

---

## CU-D08: Configuracion de Notificaciones

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El usuario tiene rol ADMIN |
| **Postcondiciones** | La configuracion de notificaciones esta actualizada |

### Flujo principal
1. El Admin accede a la configuracion de notificaciones
2. El frontend llama a `GET /notificaciones/config`
3. El backend retorna la configuracion actual (nivel_detalle)
4. El Admin modifica los campos y hace clic en "Guardar"
5. El frontend llama a `PUT /notificaciones/config`

### Criterios de aceptacion
- Solo ADMIN puede ver y editar la configuracion
- Campos: `nivel_detalle` (BAJO | ALTO)
- La configuracion de Telegram y correo se realiza en el archivo `.env` del servidor

---

## CU-D09: Generar Respaldo de BD

| Campo | Valor |
|-------|-------|
| **Actor** | Admin (manual) / Sistema (automatico, cada domingo) |
| **Precondiciones** | El usuario tiene rol ADMIN (manual) / Google Drive autorizado (automatico) |
| **Postcondiciones** | Existe un archivo .sql en Google Drive y registro en `respaldos` |

### Flujo principal (manual)
1. El Admin hace clic en "Crear respaldo"
2. Module D conecta a PostgreSQL con `asyncpg`
3. Module D genera un archivo `.sql` con la estructura y datos de todas las tablas
4. Module D sube el archivo a Google Drive en `respaldos/YYYY/MM/`
5. Module D registra en `respaldos` con estado `COMPLETADO`, `usuario_id` y `drive_file_id`

### Flujo principal (automatico)
1. Cada domingo, el sistema verifica si es dia de respaldo
2. Module D ejecuta los mismos pasos 2-5 del flujo manual
3. `usuario_id` queda `NULL` (creado por el sistema)

### Flujos alternativos
- **3a.** Si falla la generacion del .sql → se registra con estado `FALLIDO`
- **4a.** Si falla la subida a Drive → se registra con estado `FALLIDO`
- **5a.** Los respaldos expiran despues de 21 dias; se eliminan de Drive y de la BD

### Criterios de aceptacion
- El respaldo es un archivo `.sql` valido (no requiere `pg_dump`, usa `asyncpg`)
- Se genera con DELETE + INSERT (ordenado por FK) + reseteo de secuencias
- Las tablas pivote (ej: `rol_permisos`) se verifican antes de resetear secuencias
- Se registra tamano, fecha, estado, `usuario_id` y `drive_file_id`
- Respaldo automatico: solo los domingos, retencion 21 dias
- La eliminacion de respaldos expirados tambien elimina el archivo de Drive
- La pagina de respaldos muestra "Creado por" con el nombre del usuario
- La pagina de respaldos muestra aviso cuando Google Drive no esta autorizado

---

## CU-D10: Descargar Respaldo

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El respaldo existe y tiene `drive_file_id` |
| **Postcondiciones** | Se descarga el archivo .sql desde Google Drive |

### Flujo principal
1. El Admin hace clic en "Descargar" en la lista de respaldos
2. Module D obtiene el `drive_file_id` del registro
3. Module D descarga el archivo desde Google Drive
4. Module D retorna el archivo como `Response` con `application/octet-stream`

### Criterios de aceptacion
- Endpoint: `GET /respaldos/{id}/descargar`
- El archivo se descarga con nombre descriptivo
- Requiere rol ADMIN

---

## CU-D11: Restaurar Respaldo

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El respaldo existe en Drive y la BD esta operativa |
| **Postcondiciones** | La BD se restaura al estado del respaldo |

### Flujo principal
1. El Admin hace clic en "Restaurar" en la lista de respaldos
2. Module D descarga el `.sql` desde Google Drive
3. Module D deshabilita foreign keys (`SET session_replication_role = 'replica'`)
4. Module D ejecuta cada sentencia del `.sql`
5. Module D reactiva foreign keys (`SET session_replication_role = 'origin'`)

### Criterios de aceptacion
- Endpoint: `POST /respaldos/{id}/restaurar`
- Requiere rol ADMIN
- La restauracion usa `asyncpg` directo (no `psql`)

---

## CU-D12: Autorizar Google Drive (OAuth)

| Campo | Valor |
|-------|-------|
| **Actor** | Admin |
| **Precondiciones** | El usuario tiene rol ADMIN |
| **Postcondiciones** | Google Drive esta autorizado y los tokens se guardan en `oauth_tokens` |

### Flujo principal
1. El Admin ejecuta `GET /drive/auth-url` para obtener la URL de autorizacion
2. El frontend redirige al usuario a la URL de Google
3. El usuario autoriza la app en Google
4. Google redirige a `GET /drive/callback?code=CODE`
5. El backend intercambia el code por `access_token` + `refresh_token`
6. Los tokens se guardan en la tabla `oauth_tokens`

### Criterios de aceptacion
- Solo usuarios con rol ADMIN pueden autorizar
- El `access_token` se renueva automaticamente cuando expira
- Se puede verificar el estado con `GET /drive/status`
- La pagina de respaldos muestra un enlace para autorizar cuando Drive no esta autorizado

---

## CU-D13: Purgar Notificaciones Antiguas

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (cron) |
| **Precondiciones** | Hay notificaciones con mas de 30 dias |
| **Postcondiciones** | Las notificaciones antiguas se eliminan |

### Flujo principal
1. El cron se ejecuta despues del backup semanal
2. Se eliminan notificaciones con `created_at` mayor a 30 dias

### Criterios de aceptacion
- No se eliminan notificaciones de menos de 30 dias
- El script es idempotente

---

## CU-D14: Limpieza de Respaldos Expirados

| Campo | Valor |
|-------|-------|
| **Actor** | Sistema (cron, cada domingo) |
| **Precondiciones** | Hay respaldos con mas de 21 dias |
| **Postcondiciones** | Los respaldos expirados se eliminan de Drive y de la BD |

### Flujo principal
1. El cron se ejecuta cada domingo junto con el respaldo automatico
2. Se obtienen los respaldos con `expira_en < ahora`
3. Se eliminan los archivos de Google Drive
4. Se eliminan los registros de la BD

### Criterios de aceptacion
- Primero se eliminan de Drive, luego de la BD
- Si falla la eliminacion de Drive, se intenta con cada respaldo individualmente
- Se registra en logs el resultado de la limpieza

---

## Resumen de casos de uso

| CU | Nombre | Actor |
|----|--------|-------|
| CU-D01 | Generar Nota de Venta PNG | Admin/Cajero |
| CU-D02 | Descargar Notas de Venta (ZIP) | Admin |
| CU-D03 | Generar Reporte Ventas | Admin |
| CU-D04 | Generar Reporte Mas/Menor | Admin |
| CU-D05 | Exportar a Excel | Admin |
| CU-D06 | Enviar Notificacion (API) | Sistema |
| CU-D07 | Consultar Notificaciones | Admin/Cajero |
| CU-D08 | Config Notificaciones | Admin |
| CU-D09 | Generar Respaldo | Admin/Sistema |
| CU-D10 | Descargar Respaldo | Admin |
| CU-D11 | Restaurar Respaldo | Admin |
| CU-D12 | Autorizar Google Drive | Admin |
| CU-D13 | Purgar Notificaciones | Sistema |
| CU-D14 | Limpieza Respaldos Expirados | Sistema |
