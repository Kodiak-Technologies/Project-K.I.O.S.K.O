# Sistema de Notificaciones — Cambios y Contrato Inter-Módulo

**Autor:** Fabrizio
**Fecha:** 24 julio 2026
**Branch:** `feature/modulo_d_documentos`

## Resumen

Implementación del sistema de notificaciones: auto-marcar leídas, canales por rol, y documentación del contrato para que otros módulos (B, C) creen notificaciones.

## 1. Cambios realizados

### 1.1 Auto-marcar como leído al ver notificaciones

**TopBar.tsx** (campana):
- Al abrir el dropdown, se llama `marcarTodasLeidas()` automáticamente
- La campana se actualiza sin recargar la página

**Notificaciones.tsx** (página):
- Al montar la página, si hay notificaciones sin leer, se llaman `marcarTodasLeidas()` automáticamente
- El usuario no necesita hacer clic en "Marcar todas leídas"

### 1.2 Canales por rol (enviar_notificacion_usecase.py)

| Destinatario | Canales |
|-------------|---------|
| Admin (`usuario_id=None`) | Sistema (BD) + Telegram + Email |
| Trabajador (`usuario_id=valor`) | Solo Sistema (BD) |

**Lógica:**
```python
if usuario_id is None:
    # Admin: envía por todos los canales
    await sender.enviar("TELEGRAM", ...)
    await sender.enviar("CORREO", ...)
# Siempre guarda en BD (sistema)
await repo.crear(notificacion)
```

## 2. Contrato API para otros módulos

### Endpoint: `POST /notificaciones`

**Quién lo llama:** Módulos B (Inventario) y C (Ventas) cuando ocurre un evento relevante.

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token_sistema>
```

**Body:**
```json
{
  "tipo": "STOCK_BAJO",
  "titulo": "Stock bajo: Arroz 1kg",
  "mensaje": "Quedan 3 unidades (mínimo: 5). Reponer pronto.",
  "entidad_origen": "inventario",
  "entidad_id": "42",
  "usuario_id": null,
  "producto_id": 42
}
```

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `tipo` | string | Sí | `STOCK_BAJO`, `APERTURA_CAJA`, `CIERRE_CAJA`, `SOLICITUD_INGRESO`, `SISTEMA` |
| `titulo` | string | Sí | Título corto (max 120 chars) |
| `mensaje` | string | Sí | Descripción detallada |
| `entidad_origen` | string | No | Módulo de origen: `inventario`, `caja`, `ventas`, `sistema` |
| `entidad_id` | string | No | ID de la entidad que generó la notificación |
| `usuario_id` | int \| null | No | `null` = broadcast a todos (admin). Valor = solo ese usuario (trabajador) |
| `producto_id` | int \| null | No | ID del producto (para notificaciones de stock) |

### Respuesta exitosa (201):
```json
{
  "id": 123,
  "tipo": "STOCK_BAJO",
  "titulo": "Stock bajo: Arroz 1kg",
  "mensaje": "Quedan 3 unidades...",
  "leida": false,
  "created_at": "2026-07-24T12:00:00Z"
}
```

## 3. Guía para Módulo C (Ventas) — Matías

### 3.1 Notificación de apertura de caja

**Archivo:** `modules/modulo_c_ventas/application/abrir_caja_usecase.py`

**Dónde:** Después de abrir la caja exitosamente (después del `commit`).

**Código a agregar:**
```python
import httpx

# Dentro del método ejecutar(), después del commit:
try:
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://internal/notificaciones",
            json={
                "tipo": "APERTURA_CAJA",
                "titulo": "Caja abierta",
                "mensaje": f"Turno #{turno.id} abierto por {nombre_usuario}.",
                "entidad_origen": "caja",
                "entidad_id": str(turno.id),
                "usuario_id": None,  # broadcast a admin
            },
            headers={"Authorization": f"Bearer {_generar_token_sistema()}"},
        )
except Exception:
    pass  # no fallar la apertura por error de notificación
```

**Nota:** El `usuario_id=None` hace que la notificación llegue al admin por Telegram + Email + Sistema.

### 3.2 Notificación de cierre de caja

**Archivo:** `modules/modulo_c_ventas/application/cerrar_caja_usecase.py`

**Dónde:** Después de cerrar la caja exitosamente.

**Código a agregar:**
```python
# Dentro del método cerrar(), después del commit:
try:
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://internal/notificaciones",
            json={
                "tipo": "CIERRE_CAJA",
                "titulo": "Caja cerrada",
                "mensaje": f"Turno #{turno_id} cerrado por {cerrado_por}. Total: S/ {monto_final:.2f}",
                "entidad_origen": "caja",
                "entidad_id": str(turno_id),
                "usuario_id": None,
            },
            headers={"Authorization": f"Bearer {_generar_token_sistema()}"},
        )
except Exception:
    pass
```

### 3.3 Notificación de stock bajo (después de una venta)

**Archivo:** `modules/modulo_c_ventas/application/registrar_venta_usecase.py`

**Dónde:** Después de descontar stock (dentro del loop de items).

**Lógica:**
```python
# Después de cada venta de un producto:
nuevo_stock = ...  # stock actual después del descuento
producto = ...     # entidad del producto

if nuevo_stock <= producto.stock_minimo:
    # Verificar si ya existe una notificación no leída para este producto
    # (evitar duplicados hasta que se repose)
    existe = await _verificar_notificacion_stock_pendiente(producto.id)
    if not existe:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://internal/notificaciones",
                    json={
                        "tipo": "STOCK_BAJO",
                        "titulo": f"Stock bajo: {producto.nombre}",
                        "mensaje": f"Quedan {nuevo_stock} unidades (mínimo: {producto.stock_minimo}).",
                        "entidad_origen": "inventario",
                        "entidad_id": str(producto.id),
                        "usuario_id": None,  # admin recibe telegram+email
                        "producto_id": producto.id,
                    },
                    headers={"Authorization": f"Bearer {_generar_token_sistema()}"},
                )
        except Exception:
            pass
```

**Lógica de dedup ("solo 1 vez"):**
```python
async def _verificar_notificacion_stock_pendiente(producto_id: int) -> bool:
    """Retorna True si ya existe una notificación STOCK_BAJO no leída para este producto."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://internal/notificaciones",
            headers={"Authorization": f"Bearer {_generar_token_sistema()}"},
        )
        if resp.status_code == 200:
            for n in resp.json():
                if (
                    n.get("tipo") == "STOCK_BAJO"
                    and n.get("producto_id") == producto_id
                    and not n.get("leida")
                ):
                    return True
    return False
```

**Flujo:**
```
Producto: stock_minimo=5, stock_actual=6
Venta → stock=5 → ¿existe notif no leída? NO → crear notificación
Venta → stock=4 → ¿existe notif no leída? SÍ → NO crear
Admin lee la notificación (o pasa 30 días y se purga)
Stock se repone a 7
Venta → stock=6 → ¿existe notif no leída? NO (ya fue leída) → NO crear (aún sobre mínimo)
Venta → stock=5 → ¿existe notif no leída? NO → crear nueva notificación
```

## 4. Pendiente para futuro

### 4.1 Módulo B (Inventario) — Brayan
- **SOLICITUD_INGRESO:** Crear notificación cuando se apruebe/rechace un ingreso
- **FECHA_POR_VENCER:** Cron task que verifique productos con fecha de vencimiento próxima
- El módulo de ingresos está completamente vacío (stubs). Necesita implementación completa.

### 4.2 Notificación de trabajador
- Para notificaciones de stock bajo dirigidas a un trabajador específico:
  ```json
  {"usuario_id": 5, ...}
  ```
  Solo aparece en el sistema del trabajador (sin Telegram ni Email).

## 5. Tipos de notificación

| Tipo | Descripción | Canales | Quién recibe |
|------|-------------|---------|--------------|
| `STOCK_BAJO` | Producto alcanzó o cruzó el stock mínimo | Sistema + Telegram + Email | Admin (broadcast) |
| `APERTURA_CAJA` | Se abrió la caja del turno | Sistema + Telegram + Email | Admin (broadcast) |
| `CIERRE_CAJA` | Se cerró la caja del turno | Sistema + Telegram + Email | Admin (broadcast) |
| `SOLICITUD_INGRESO` | Solicitud de reposición de producto | Sistema + Telegram + Email | Admin (broadcast) |
| `SISTEMA` | Notificaciones del sistema (respaldos, etc.) | Sistema + Telegram + Email | Admin (broadcast) |
