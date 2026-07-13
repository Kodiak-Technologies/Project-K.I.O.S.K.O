# Frontend: sistema de diseño y vistas — guía para los 4

Este documento explica cómo está construida la interfaz, qué componentes compartidos existen y **cuál es el objetivo de cada pantalla**. Léelo antes de tocar cualquier página de tu módulo: los componentes ya resuelven el 90% del trabajo visual y usarlos mantiene la UI consistente entre los 4 módulos.

---

## 1. Filosofía visual (decidida el 2026-07-12)

- **Base en escala de grises** (paleta `zinc` de Tailwind): fondo `zinc-50`, tarjetas blancas, bordes `zinc-200`, texto principal `zinc-900`.
- **El color significa algo.** Solo se usa color para **estados**: verde = éxito/activo, rojo = error/peligro, amarillo = advertencia/pendiente, azul = información. Nunca como decoración.
- **Regla de contraste**: los colores de estado van como *fondo suave + texto oscuro* (ej. badge verde claro con texto verde oscuro). Las versiones intensas solo para puntos, bordes e íconos. Nunca texto amarillo o verde claro sobre blanco.
- **PROHIBIDO usar emojis en la UI.** Los íconos son componentes React de `lucide-react` (`<Package />`, `<Wallet />`, etc.).
- **Solo tema claro.**
- **Responsive real**: denso en escritorio, táctil en tablet. Todo botón, input e ítem de navegación mide mínimo 44px de alto (`min-h-tactil`).
- **Acento de marca configurable**: la dueña puede cambiar el color primario/secundario y la tipografía desde Configuración. Esos valores viajan como variables CSS (`--color-primario`, `--color-secundario`, `--tipografia`) y en Tailwind se usan como `text-marca`, `bg-marca`, etc. El default es gris casi negro (`#18181b`). El primario pinta los **botones primarios, el bloque del logo y el ítem activo del sidebar**; el secundario, los íconos de los accesos rápidos del Inicio. **No** los uses para estados — para eso están los tonos de abajo.

### Tokens (en `tailwind.config.ts`)

| Token | Uso | Clases |
|---|---|---|
| `marca` | Color primario de la dueña: botones primarios, bloque del logo, ítem activo del sidebar, foco | `bg-marca`, `text-marca`, `ring-marca` |
| `marca-secundario` | Color secundario de la dueña: íconos de los accesos rápidos del Inicio | `text-marca-secundario` |
| `exito` (+ `-suave`, `-intenso`) | Operación correcta, activo, caja abierta | `bg-exito-suave text-green-800` |
| `peligro` (+ variantes) | Errores, eliminar, anular, sin stock | `bg-peligro-suave text-red-800` |
| `alerta` (+ variantes) | Pendiente, stock bajo, bloqueos | `bg-alerta-suave text-yellow-800` |
| `info` (+ variantes) | Información neutra | `bg-info-suave text-blue-800` |
| `min-h-tactil` | Altura táctil mínima (44px) | botones, inputs, nav |
| `shadow-tarjeta` | La única sombra del sistema | tarjetas y popovers |

---

## 2. Componentes compartidos (`src/shared/components/ui/`)

Importa siempre desde el barrel:

```tsx
import { Button, Card, Table, Badge, Modal, Input, Select,
         Alert, EmptyState, ModuloPendiente, PageSpinner, PageHeader,
         type Columna, type Tono } from "../../../shared/components/ui";
```

| Componente | Para qué sirve | Notas |
|---|---|---|
| `Button` | Toda acción clickeable | `variante`: `primario` (gris casi negro), `secundario` (borde), `peligro`, `fantasma`. Props: `compacto`, `cargando`, `icono` |
| `Input` / `Select` | Campos de formulario | Con `label`, `error` y `requerido` integrados |
| `Card` | Superficie blanca | Props `titulo`, `descripcion`, `accion`, `sinPadding` (para tablas) |
| `Badge` | Estados en tablas | `tono`: `exito`/`peligro`/`alerta`/`info`/`neutro`, con punto de color |
| `Table` | Toda tabla del sistema | Genérica: `columnas` (render props), `filas`, `claveDe`, `vacio`. Columnas con `soloEscritorio` se ocultan en pantallas chicas; el scroll horizontal es interno |
| `Modal` | Formularios y confirmaciones | Cierra con Escape/fondo. Nada de `window.prompt`/`confirm` |
| `Alert` | Mensajes de éxito/error tras una acción | `role="alert"` incluido |
| `EmptyState` | Cuando una lista está vacía | Ícono + título + descripción + acción opcional |
| `ModuloPendiente` | Cuando el backend de tu módulo aún no responde | Ver §4 |
| `PageSpinner` | Carga inicial de página | |
| `PageHeader` | Título + descripción + acciones de cada página | Siempre el primer elemento de una página |

## 3. Layout

- **Sidebar izquierdo** (`shared/components/Sidebar.tsx`): navegación agrupada por módulo (Ventas, Inventario, Documentos, Seguridad), filtra ítems `soloAdmin` según el rol, y **Configuración va SIEMPRE anclada al fondo** (decisión de diseño). En escritorio es fijo; en tablet/móvil es un drawer que abre la hamburguesa de la topbar.
- **TopBar** (`shared/components/TopBar.tsx`): blanca y mínima — hamburguesa (solo pantallas chicas), **campanita de notificaciones** (badge con el conteo de no leídas y popover con las entrantes; el historial completo, leídas incluidas, vive en la página Notificaciones del sidebar) y logout. La personalización de colores/tipografía se hace en Configuración.
- Para agregar una página de tu módulo: crea la page, regístrala en el `routes.tsx` de tu módulo (ya montado en `App.tsx`) y agrega el enlace en `GRUPOS` de `Sidebar.tsx` con su ícono de lucide.

---

## 4. Objetivo de cada vista

La lógica general: **las vistas de consulta son de ambos roles; las que mueven dinero, stock o cuentas son solo del ADMIN**, y todo lo delicado deja huella en la bitácora.

### Transversales
| Vista | Ruta | Objetivo |
|---|---|---|
| Login | `/login` | Autenticar. No hay registro: las cuentas las crea el ADMIN. Usernames siempre en minúsculas |
| Inicio | `/` | Atajos a lo más usado según el rol. No es pantalla de trabajo |

### Módulo C — Ventas (operación diaria)
| Vista | Ruta | Objetivo |
|---|---|---|
| Punto de venta | `/pos` | Cobrar rápido: productos como botones táctiles, carrito al lado, método de pago y listo. No deja cobrar con caja cerrada |
| Caja | `/caja` | Abrir turno declarando el efectivo inicial. Sin turno abierto no hay ventas |
| Cierre de caja | `/caja/cierre` | Contar el efectivo real al final; el sistema compara contra lo esperado y registra la diferencia (control antifraude) |
| Historial | `/historial-ventas` | Qué se vendió y cuándo. El ADMIN puede anular con motivo (devuelve stock, queda en bitácora; nunca se borra) |

### Módulo B — Inventario (que el stock no mienta)
| Vista | Ruta | Objetivo |
|---|---|---|
| Catálogo | `/catalogo` | Consulta de stock y precios para ambos roles. Verde = disponible, amarillo = stock bajo, rojo = agotado |
| Gestión de productos | `/productos` (ADMIN) | Alta/edición de productos, precios y categorías |
| Ingresos | `/ingresos` | El CAJERO registra la mercadería que llega; queda PENDIENTE, no suma stock todavía |
| Aprobaciones | `/aprobaciones` (ADMIN) | El ADMIN aprueba (recién ahí suma stock) o rechaza con motivo. Control de 4 manos: nadie infla el inventario solo |

### Módulo D — Documentos (memoria del negocio)
| Vista | Ruta | Objetivo |
|---|---|---|
| Boletas | `/boletas` | Buscar comprobantes por fecha y descargar el PDF |
| Reportes | `/reportes` (ADMIN) | Cómo va el negocio: total vendido, n° de ventas, ticket promedio, top de productos por período |
| Notificaciones | `/notificaciones` | Avisos automáticos: stock bajo, cierres de caja, sistema |

### Módulo A — Seguridad
| Vista | Ruta | Objetivo |
|---|---|---|
| Usuarios | `/usuarios` (ADMIN) | Alta de personal, desactivar, resetear contraseña, borrado lógico |
| Bitácora | `/bitacora` (ADMIN) | Registro inmutable con filtros: responder "¿quién hizo qué?" en menos de un minuto |
| Configuración | `/configuracion` (ADMIN) | Identidad visual (nombre, logo, colores, tipografía) y reglas de seguridad (TTL de sesión, intentos, bloqueo) |

---

## 5. Backend pendiente (importante para B, C y D)

Las páginas de los módulos B, C y D **ya están implementadas y funcionan**, pero sus backends aún no existen. Cuando el adaptador HTTP recibe 404/501/503 o error de red, la página muestra `ModuloPendiente` en vez de romperse (helper `servicioNoDisponible()` en `shared/lib/http-client.ts`).

**Qué te toca**: implementar los endpoints con el contrato que el frontend ya espera — está definido en los `*.port.ts` y `types/index.ts` de tu módulo, y documentado en [FRONTEND_CONTRATOS_API.md](FRONTEND_CONTRATOS_API.md). Si respetas ese contrato, tu pantalla funciona sin tocar una línea de React. Si necesitas cambiarlo, coordínalo con Matías (dueño del frontend).
