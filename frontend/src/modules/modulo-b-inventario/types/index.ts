// Tipos/DTOs del módulo de inventario (contrato esperado del backend de Brayan).
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/schemas.py.
//
// Convenciones:
//   - `interface` para objetos, `type` para uniones/aliases.
//   - Los nombres de campos matchean 1:1 con el backend (snake_case).
//   - PR3a: se agregaron `PaginadosResponse<T>`, shapes de SolicitudIngreso con
//     `lineas[]`, Merma, Proveedor, PagoProveedor, MovimientoInventario, StorageResult
//     y filtros para los endpoints de listado.

// =============================================================================
// Paginación (helper genérico para todos los listados del módulo)
// =============================================================================

/** Shape de respuesta paginada del backend (`ProductosPaginadosResponse`,
 *  `IngresosPaginadosResponse`, `MermasPaginadosResponse`, etc.). */
export interface PaginadosResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** Filtros comunes para los listados paginados del módulo B. */
export interface FiltrosPaginacion {
  page?: number;
  page_size?: number;
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
  foto_url: string | null;
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
  foto_url?: string | null;
}

/** `PATCH /productos/{id}`. NO incluye precios (van por `/precio`). */
export interface EdicionProducto {
  codigo?: string;
  nombre?: string;
  categoria_id?: number | null;
  stock_minimo?: number;
  activo?: boolean;
  es_codigo_interno?: boolean;
  foto_url?: string | null;
}

/** `PATCH /productos/{id}/precio`. Hay que enviar al menos uno. */
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

/** Una línea de la solicitud de ingreso. */
export interface DetalleSolicitud {
  id: number;
  producto_id: number;
  cantidad: number;
  precio_compra_unitario: number;
}

/** Body para `POST /ingresos`. Mínimo 1 línea, `foto_boleta_url` obligatorio. */
export interface NuevaSolicitudIngreso {
  proveedor_id?: number | null;
  foto_boleta_url: string;
  lineas: DetalleSolicitudCreate[];
}

/** Una línea del body de `POST /ingresos` (sin `id`, lo asigna el backend). */
export interface DetalleSolicitudCreate {
  producto_id: number;
  cantidad: number;
  precio_compra_unitario: number;
}

/** `GET /ingresos` (cada item) y `GET /ingresos/{id}`. */
export interface SolicitudIngreso {
  id: number;
  proveedor_id: number | null;
  estado: EstadoIngreso | string;
  foto_boleta_url: string;
  motivo_rechazo: string | null;
  lineas: DetalleSolicitud[];
  solicitado_por_nombre: string;
  revisado_por_nombre: string | null;
  revisado_en: string | null;
  created_at: string | null;
  cantidad_productos: number | null;
  monto_total: number | null;
}

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
}

/** Filtros para `GET /ingresos`. */
export interface FiltrosIngresos extends FiltrosPaginacion {
  estado?: EstadoIngreso;
  proveedor_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
}

// =============================================================================
// Mermas
// =============================================================================

export type EstadoMerma = "Registrada" | "Confirmada" | "Rechazada";

export type MotivoMerma = "vencimiento" | "rotura" | "otro";

/** `POST /mermas`. */
export interface NuevaMerma {
  producto_id: number;
  cantidad: number;
  motivo: MotivoMerma;
  observacion?: string | null;
  proveedor_id?: number | null;
}

/** `GET /mermas` (cada item) y `GET /mermas/{id}`. */
export interface Merma {
  id: number;
  producto_id: number;
  cantidad: number;
  motivo: MotivoMerma | string;
  observacion: string | null;
  estado: EstadoMerma | string;
  registrado_por_nombre: string;
  confirmado_por_nombre: string | null;
  confirmado_en: string | null;
  rechazado_por_nombre: string | null;
  rechazado_en: string | null;
  motivo_rechazo: string | null;
  created_at: string | null;
}

/** Body para `POST /mermas/{id}/rechazar`. */
export interface RechazoMerma {
  motivo_rechazo: string;
}

/** Respuesta de `POST /mermas/{id}/confirmar`. */
export interface ConfirmacionMerma {
  id: number;
  estado: string;
  confirmado_por_nombre: string;
  confirmado_en: string | null;
  stock_actualizado: number | null;
}

/** Filtros para `GET /mermas`. */
export interface FiltrosMermas extends FiltrosPaginacion {
  estado?: EstadoMerma;
  motivo?: MotivoMerma;
  producto_id?: number;
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

export type TipoMovimiento = "ingreso" | "merma" | "venta" | "devolucion" | "ajuste";

/** `GET /inventario/movimientos` (cada item). */
export interface MovimientoInventario {
  id: number;
  producto_id: number;
  cantidad: number;
  tipo: TipoMovimiento | string;
  motivo: string | null;
  solicitud_ingreso_id: number | null;
  merma_id: number | null;
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
  expires_at: string | null;
}
