// Puerto: interfaz de registro/aprobación/rechazo de ingresos de mercadería.
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/ingresos_router.py
import type {
  AprobacionIngreso,
  FiltrosIngresos,
  NuevaSolicitudIngreso,
  PaginadosResponse,
  RechazoIngreso,
  SolicitudIngreso,
  SolicitudIngresoUpdateBody,
} from "../types";

export interface IngresosPort {
  /** `GET /ingresos` (paginado, con filtros opcionales). */
  listar(filtros?: FiltrosIngresos): Promise<PaginadosResponse<SolicitudIngreso>>;
  /** `GET /ingresos/{id}`. */
  obtener(id: number): Promise<SolicitudIngreso>;
  /** Alias de `obtener` (sdd/modulo-b-aprobaciones-detalle-editar). */
  obtenerPorId(id: number): Promise<SolicitudIngreso>;
  /** `POST /ingresos`. Body: proveedor opcional + foto obligatoria + líneas. */
  solicitar(datos: NuevaSolicitudIngreso): Promise<SolicitudIngreso>;
  /** `POST /ingresos/{id}/aprobar`. Devuelve `AprobacionIngreso` (no la solicitud). */
  aprobar(id: number): Promise<AprobacionIngreso>;
  /** `POST /ingresos/{id}/rechazar`. Body: `{ motivo_rechazo }`. */
  rechazar(id: number, datos: RechazoIngreso): Promise<SolicitudIngreso>;
  /** sdd/modulo-b-aprobaciones-detalle-editar: `PATCH /ingresos/{id}`. */
  editar(id: number, body: SolicitudIngresoUpdateBody): Promise<SolicitudIngreso>;
}
