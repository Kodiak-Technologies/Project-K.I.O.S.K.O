// Puerto: interfaz de gestión de productos (listar, crear, actualizar, precios).
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/productos_router.py
import type {
  CambioPrecio,
  CambioPrecioRespuesta,
  EdicionProducto,
  FiltrosProductos,
  HistorialPrecioItem,
  NuevoProducto,
  PaginadosResponse,
  PorReponerItem,
  Producto,
} from "../types";

export interface ProductosPort {
  /** `GET /productos` con filtros opcionales. */
  listar(filtros?: FiltrosProductos): Promise<PaginadosResponse<Producto>>;
  /** `GET /productos/{id}`. */
  obtener(id: number): Promise<Producto>;
  /** `GET /productos/buscar?codigo=…` (devuelve 1) o `?nombre=…` (devuelve varios). */
  buscar(codigo?: string, nombre?: string, categoria_id?: number): Promise<Producto | Producto[]>;
  /** `GET /productos/por-reponer` (productos bajo mínimo o sin stock). */
  porReponer(filtros?: { categoria_id?: number; page?: number; page_size?: number }): Promise<PaginadosResponse<PorReponerItem>>;
  /** `POST /productos`. */
  crear(datos: NuevoProducto): Promise<Producto>;
  /** `PATCH /productos/{id}`. NO incluye precios. */
  actualizar(id: number, datos: EdicionProducto): Promise<Producto>;
  /** `PATCH /productos/{id}/precio`. */
  cambiarPrecio(id: number, datos: CambioPrecio): Promise<CambioPrecioRespuesta>;
  /** `GET /productos/{id}/historial-precios`. */
  historialPrecios(id: number, filtros?: { tipo?: string; page?: number; page_size?: number }): Promise<PaginadosResponse<HistorialPrecioItem>>;
}
