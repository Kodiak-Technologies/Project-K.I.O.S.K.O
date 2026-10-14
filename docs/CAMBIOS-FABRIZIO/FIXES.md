# Fixes — Registro de correcciones

Este archivo es el registro de **correcciones puntuales (fixes)**. Cada fix nuevo
se agrega al final, en orden cronológico, con el mismo formato de plantilla:

```
## Fix N — <título corto>

**Fecha:** <día mes año>
**Branch:** `<rama>`
**Módulo/área:** <a qué módulo o pantalla afecta>
**Afecta BD:** <sí/no (¿requiere migración?)>

### Problema
<qué veía el usuario / qué fallaba>

### Causa
<por qué pasaba>

### Solución
<qué se cambió>

### Archivos modificados
- <ruta>

### Notas
<observaciones, pendientes, cómo verificarlo>
```

---

## Fix 1 — Historial de turnos no mostraba días anteriores

**Fecha:** 13 octubre 2026
**Branch:** `fix/caja-historial-turnos`
**Módulo/área:** Módulo C (Ventas/Caja) — pantalla `/caja` → "Historial de turnos"
**Afecta BD:** No

### Problema
En **Caja → Historial de turnos** se veían los turnos del día actual, pero al
elegir una fecha de días anteriores (p. ej. hace 3 días) la tabla aparecía vacía
con el mensaje "Sin turnos para este día", aunque esos turnos sí existían.

### Causa
El backend solo devolvía los **últimos 30 turnos** (`GET /caja/turnos?limite=30`)
y **nunca filtraba por fecha**. La pantalla elegía la fecha, pero el filtro se
hacía **en el navegador** sobre esa lista ya recortada. Si el día buscado no
estaba entre los últimos 30 turnos, no había con qué llenar la tabla.

### Solución
Se agregó filtrado por fecha en el backend y la pantalla ahora pide al servidor
los turnos del día seleccionado (`?desde=&hasta=`), en lugar de filtrar en el
cliente. Los parámetros son opcionales: sin ellos el endpoint se comporta igual
que antes (turnos más recientes), por lo que no rompe a otros consumidores.

El rango se calcula en la zona horaria del negocio (`America/Lima`), igual que en
el módulo de ventas, para no correr el corte de día.

### Archivos modificados
- `backend/app/modules/modulo_c_ventas/domain/ports/caja_repository_port.py`
- `backend/app/modules/modulo_c_ventas/infrastructure/adapters/database/sqlalchemy_caja_repository.py`
- `backend/app/modules/modulo_c_ventas/application/consultar_caja_usecase.py`
- `backend/app/modules/modulo_c_ventas/infrastructure/http/caja_router.py`
- `frontend/src/modules/modulo-c-ventas/services/caja.port.ts`
- `frontend/src/modules/modulo-c-ventas/services/caja.http-adapter.ts`
- `frontend/src/modules/modulo-c-ventas/hooks/useCaja.ts`
- `frontend/src/modules/modulo-c-ventas/pages/AperturaCaja.tsx`

### Notas
- No requiere migraciones ni cambios en la base de datos.
- Tabla en BD para inspeccionar los turnos: **`turnos_caja`** (la fecha de
  apertura es la columna `abierto_en`, TIMESTAMPTZ; los montos y el estado están
  en `monto_inicial`, `monto_final`, `estado`). Los arqueos/descuadres están en
  **`arqueos`** (por `turno_id`).
- Verificación: abrir `/caja`, elegir una fecha con más de 30 turnos acumulados y
  confirmar que aparecen los turnos de ese día.
