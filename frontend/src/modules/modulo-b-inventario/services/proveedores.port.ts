// Puerto: interfaz de gestión de proveedores y deuda (HU-B14).
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/proveedores_router.py
import type {
  EdicionProveedor,
  FiltrosPagosProveedor,
  FiltrosProveedores,
  NuevoPagoProveedor,
  NuevoProveedor,
  PagosPaginadosResponse,
  PaginadosResponse,
  PagoProveedor,
  Proveedor,
} from "../types";

export interface ProveedoresPort {
  /** `GET /proveedores` (paginado, con filtros opcionales). */
  listar(filtros?: FiltrosProveedores): Promise<PaginadosResponse<Proveedor>>;
  /** `GET /proveedores/{id}`. */
  obtener(id: number): Promise<Proveedor>;
  /** `POST /proveedores`. */
  crear(datos: NuevoProveedor): Promise<Proveedor>;
  /** `PATCH /proveedores/{id}`. NO incluye `deuda_actual`. */
  editar(id: number, datos: EdicionProveedor): Promise<Proveedor>;
  /** `POST /proveedores/{id}/compras-credito`. */
  registrarCompraCredito(id: number, datos: NuevoPagoProveedor): Promise<PagoProveedor>;
  /** `POST /proveedores/{id}/pagos`. */
  registrarPago(id: number, datos: NuevoPagoProveedor): Promise<PagoProveedor>;
  /** `GET /proveedores/{id}/pagos` (paginado, con `deuda_actual` global). */
  listarPagos(proveedorId: number, filtros?: FiltrosPagosProveedor): Promise<PagosPaginadosResponse>;
}
