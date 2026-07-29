// Tipos/DTOs del módulo de inventario (contrato esperado del backend de Brayan).
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/schemas.py.
//
// Convenciones:
//   - `interface` para objetos, `type` para uniones/aliases.
//   - Los nombres de campos matchean 1:1 con el backend (snake_case).
//   - PR3a: se agregaron `PaginadosResponse<T>`, shapes de SolicitudIngreso con
//     `lineas[]`, Proveedor, PagoProveedor, MovimientoInventario, StorageResult
//     y filtros para los endpoints de listado.

// =============================================================================
// Paginación (helper genérico para todos los listados del módulo)
// =============================================================================

/** Shape de respuesta paginada del backend (`ProductosPaginadosResponse`,
 *  `IngresosPaginadosResponse`, `ProveedoresPaginadosResponse`, etc.). */
export interface PaginadosResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  /** Cursor de la última fila (solo en los listados que se escriben en
   *  caliente: movimientos e ingresos). Ver `usePaginacionCursor`. */
  siguiente_cursor?: string | null;
}

/** Filtros comunes para los listados paginados del módulo B. */
export interface FiltrosPaginacion {
  page?: number;
  page_size?: number;
  /** Paginación por cursor: si va, el backend ignora `page`. Evita que las
   *  filas nuevas corran las páginas mientras el usuario navega. */
  cursor?: string;
}

// =============================================================================
// Categorías
// =============================================================================

export interface Categoria {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
  creado_por_nombre: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** Body para `POST /categorias`. `descripcion` es opcional. */
export interface NuevaCategoria {
  nombre: string;
  descripcion?: string | null;
}

/** Body para `PATCH /categorias/{id}`. Todos los campos son opcionales. */
export interface EdicionCategoria {
  nombre?: string;
  descripcion?: string | null;
  activo?: boolean;
}

// =============================================================================
// Productos
// =============================================================================

/** `GET /productos/{id}` y cada item de `GET /productos`. */
export interface Producto {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number | null;
  categoria_nombre: string | null;
  /** Alias semántico de `precio_venta` (lo devuelve el backend por compat con
   *  catálogos legacy). Para escritura usá `precio_venta`. */
  precio: number;
  precio_venta: number;
  precio_compra_actual: number;
  stock: number;
  stock_minimo: number;
  activo: boolean;
  es_codigo_interno: boolean;
  creado_por_nombre: string | null;
  actualizado_por_nombre: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** `POST /productos`. El backend exige `precio_venta` (>0) y `precio_compra_actual` (>=0). */
export interface NuevoProducto {
  codigo?: string | null;
  nombre: string;
  categoria_id?: number | null;
  precio_venta: number;
  precio_compra_actual: number;
  stock_minimo?: number;
  stock_inicial?: number;
  es_codigo_interno?: boolean;
}

/** `PATCH /productos/{id}`. NO incluye precios (van por `/precio`). */
export interface EdicionProducto {
  codigo?: string;
  nombre?: string;
  categoria_id?: number | null;
  stock_minimo?: number;
  activo?: boolean;
  es_codigo_interno?: boolean;
}

/** `PATCH /productos/{id}/precio`. Hay que enviar al menos un precio. */
export interface CambioPrecio {
  precio_venta?: number;
  precio_compra_actual?: number;
}

/** `GET /productos/por-reponer`. Items con faltante calculado. */
export interface PorReponerItem {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number | null;
  categoria_nombre: string | null;
  stock: number;
  stock_minimo: number;
  faltante: number;
}

/** Item de `GET /productos/{id}/historial-precios`. */
export interface HistorialPrecioItem {
  id: number;
  tipo_precio: string;
  precio_anterior: number | null;
  precio_nuevo: number;
  modificado_por_nombre: string;
  created_at: string | null;
}

/** Respuesta de `PATCH /productos/{id}/precio`. */
export interface CambioPrecioRespuesta {
  producto: Producto;
  historial_registrado: boolean;
  filas_historial: HistorialPrecioItem[];
}

/** Filtros para `GET /productos`. */
export interface FiltrosProductos extends FiltrosPaginacion {
  search?: string;
  categoria_id?: number;
  solo_con_stock?: boolean;
  solo_bajo_minimo?: boolean;
  /** Solo los agotados (stock = 0). */
  sin_stock?: boolean;
  precio_min?: number;
  precio_max?: number;
  activo?: boolean;
}

// =============================================================================
// Solicitudes de ingreso (ingresos de mercadería)
// =============================================================================

export type EstadoIngreso = "Pendiente" | "Aprobada" | "Rechazada";

/** Alias de compat: la forma canónica nueva es `SolicitudIngreso` (con
 *  `lineas[]`, `proveedor_id`, `foto_boleta_url`). Las páginas legadas
 *  importaban `IngresoMercaderia`; se conserva el nombre para no romperlas
 *  hasta PR3b. */
export type IngresoMercaderia = SolicitudIngreso;

/** Una línea de la solicitud de ingreso.
 *  `producto_nombre` / `producto_codigo` los resuelve el backend con un JOIN:
 *  no hace falta cargar el catálogo para mostrarlos. */
export interface DetalleSolicitud {
  id: number;
  /** null mientras el producto todavía no se creó (solicitud sin aprobar). */
  producto_id: number | null;
  producto_nombre: string | null;
  producto_codigo: string | null;
  cantidad: number;
  /** Monto de la línea tal cual la boleta ("7 esponjas — S/ 20"). */
  precio_compra_total: number;
  /** Derivado por el backend (total / cantidad). Solo para mostrar. */
  precio_compra_unitario: number;
  es_producto_nuevo: boolean;
  nuevo_codigo: string | null;
  nuevo_nombre: string | null;
  nuevo_categoria_id: number | null;
  /** % de ganancia de la línea. null = usar el del negocio. */
  margen_ganancia: number | null;
}

/** Body para `POST /ingresos`. Mínimo 1 línea, `foto_boleta_url` obligatorio. */
export interface NuevaSolicitudIngreso {
  proveedor_id?: number | null;
  foto_boleta_url: string;
  lineas: DetalleSolicitudCreate[];
}

/** Una línea del body de `POST /ingresos` (sin `id`, lo asigna el backend).
 *
 *  O trae `producto_id` (producto del catálogo), o `nuevo_codigo` +
 *  `nuevo_nombre` para dar de alta uno que todavía no existe: el cajero no
 *  necesita que un ADMIN lo cree antes para poder transcribir la boleta.
 *  `precio_compra_total` es el monto de la línea, NO el unitario. */
export interface DetalleSolicitudCreate {
  cantidad: number;
  precio_compra_total: number;
  producto_id?: number | null;
  nuevo_codigo?: string | null;
  nuevo_nombre?: string | null;
  nuevo_categoria_id?: number | null;
  margen_ganancia?: number | null;
}

/** `GET /ingresos` (cada item) y `GET /ingresos/{id}`. */
export interface SolicitudIngreso {
  id: number;
  proveedor_id: number | null;
  estado: EstadoIngreso | string;
  foto_boleta_url: string;
  motivo_rechazo: string | null;
  motivo: string | null; // sdd/modulo-b-aprobaciones-detalle-editar
  lineas: DetalleSolicitud[];
  solicitado_por: number; // sdd/modulo-b-aprobaciones-detalle-editar (id del creador, para gate)
  solicitado_por_nombre: string;
  revisado_por_nombre: string | null;
  revisado_en: string | null;
  editado_por: number | null;
  editado_por_nombre: string | null;
  editado_en: string | null;
  created_at: string | null;
  updated_at: string | null;
  cantidad_productos: number | null;
  monto_total: number | null;
}

/** sdd/modulo-b-aprobaciones-detalle-editar: body para `PATCH /ingresos/{id}`. */
export interface SolicitudIngresoUpdateBody {
  proveedor_id?: number | null;
  motivo?: string | null;
  lineas?: LineaIngresoUpdate[] | null; // null = no tocar; [] = borrar todas
}

export interface LineaIngresoUpdate {
  cantidad: number;
  precio_compra_total: number;
  producto_id?: number | null;
  nuevo_codigo?: string | null;
  nuevo_nombre?: string | null;
  nuevo_categoria_id?: number | null;
  margen_ganancia?: number | null;
}

/** Body de `POST /productos/{id}/ajustar-stock` (solo ADMIN). */
export interface AjusteStock {
  /** Positivo suma, negativo descuenta. Distinto de 0. */
  delta: number;
  /** Queda en el asiento de `movimientos_inventario` y en la bitácora. */
  motivo: string;
}

/** Respuesta de `POST /productos/{id}/ajustar-stock`. */
export interface AjusteStockRespuesta {
  producto: Producto;
  stock_anterior: number;
  stock_actual: number;
  delta: number;
}

/** Body opcional de `DELETE /productos/{id}`. */
export interface BajaProducto {
  motivo?: string | null;
}

/** Códigos de error estructurados del backend (NFR-5). */
export type ErrorCodeBackend =
  | "EMPTY_PATCH"
  | "NOT_EDITABLE_STATE"
  | "FORBIDDEN"
  | "PRODUCT_NOT_FOUND"
  | "PROVEEDOR_NOT_FOUND"
  | "INVALID_LINE_VALUES"
  | "INVALID_CANTIDAD"
  | "STOCK_INSUFICIENTE"
  | "MOTIVO_REQUERIDO"
  | "INVALID_MOTIVO"
  | "UNKNOWN_FIELD"
  | "CONCURRENT_EDIT"
  | "INGRESO_NOT_FOUND"
  | "ALREADY_REJECTED"
  | "MOTIVO_RECHAZO_TOO_SHORT";

/** Body para `POST /ingresos/{id}/rechazar`. */
export interface RechazoIngreso {
  motivo_rechazo: string;
}

/** Respuesta de `POST /ingresos/{id}/aprobar`. */
export interface AprobacionIngreso {
  id: number;
  estado: string;
  revisado_por_nombre: string;
  revisado_en: string | null;
  productos_actualizados: number;
  unidades_agregadas: number;
  /** Productos dados de alta en el catálogo al aprobar. */
  productos_creados?: number;
}

/** Filtros para `GET /ingresos`. */
export interface FiltrosIngresos extends FiltrosPaginacion {
  estado?: EstadoIngreso;
  proveedor_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
}

// =============================================================================
// Proveedores
// =============================================================================

export interface Proveedor {
  id: number;
  razon_social: string;
  ruc: string | null;
  telefono: string | null;
  email: string | null;
  direccion: string | null;
  activo: boolean;
  deuda_actual: number;
  creado_por_nombre: string;
  created_at: string | null;
  updated_at: string | null;
}

/** `POST /proveedores`. */
export interface NuevoProveedor {
  razon_social: string;
  ruc?: string | null;
  telefono?: string | null;
  email?: string | null;
  direccion?: string | null;
}

/** `PATCH /proveedores/{id}`. NO incluye `deuda_actual` (lo mueven pagos/compras). */
export interface EdicionProveedor {
  razon_social?: string;
  ruc?: string | null;
  telefono?: string | null;
  email?: string | null;
  direccion?: string | null;
  activo?: boolean;
}

/** Filtros para `GET /proveedores`. */
export interface FiltrosProveedores extends FiltrosPaginacion {
  search?: string;
  solo_con_deuda?: boolean;
  activo?: boolean;
}

// =============================================================================
// Pagos a proveedor
// =============================================================================

export type TipoPago = "COMPRA_CREDITO" | "PAGO";

/** Body compartido para `POST /{id}/compras-credito` y `POST /{id}/pagos`. */
export interface NuevoPagoProveedor {
  monto: number;
  /** ISO date (YYYY-MM-DD). */
  fecha: string;
  concepto?: string | null;
  solicitud_ingreso_id?: number | null;
}

/** Cada item de `GET /{id}/pagos` y respuesta de los POST. */
export interface PagoProveedor {
  id: number;
  tipo: TipoPago | string;
  monto: number;
  concepto: string | null;
  /** ISO date (YYYY-MM-DD). */
  fecha: string;
  solicitud_ingreso_id: number | null;
  registrado_por_nombre: string;
  created_at: string | null;
  /** Deuda del proveedor tras la operación. */
  deuda_actual: number;
}

/** `GET /{id}/pagos`: la respuesta paginada además trae `deuda_actual` global. */
export interface PagosPaginadosResponse extends PaginadosResponse<PagoProveedor> {
  deuda_actual: number;
}

/** Filtros para `GET /{id}/pagos`. */
export interface FiltrosPagosProveedor extends FiltrosPaginacion {
  tipo?: TipoPago;
  fecha_desde?: string;
  fecha_hasta?: string;
}

// =============================================================================
// Movimientos de inventario (bitácora append-only)
// =============================================================================

export type TipoMovimiento = "ingreso" | "venta" | "devolucion" | "ajuste";

/** `GET /inventario/movimientos` (cada item). */
export interface MovimientoInventario {
  id: number;
  producto_id: number;
  producto_nombre: string | null;
  producto_codigo: string | null;
  cantidad: number;
  tipo: TipoMovimiento | string;
  motivo: string | null;
  solicitud_ingreso_id: number | null;
  registrado_por_nombre: string;
  created_at: string | null;
}

/** Filtros para `GET /inventario/movimientos`. */
export interface FiltrosMovimientos extends FiltrosPaginacion {
  producto_id?: number;
  tipo?: TipoMovimiento;
  fecha_desde?: string;
  fecha_hasta?: string;
}

// =============================================================================
// Storage (subida de archivos)
// =============================================================================

/** Respuesta de `POST /storage/upload`. */
export interface StorageResult {
  url: string;
  path: string;
  filename: string;
  mime: string;
  size_bytes: number;
}
