// Puerto: interfaz de registro, confirmación y rechazo de mermas.
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/mermas_router.py
import type {
  ConfirmacionMerma,
  FiltrosMermas,
  Merma,
  MermaUpdateBody,
  NuevaMerma,
  PaginadosResponse,
  RechazoMerma,
} from "../types";

export interface MermasPort {
  /** `GET /mermas` (paginado, con filtros opcionales). */
  listar(filtros?: FiltrosMermas): Promise<PaginadosResponse<Merma>>;
  /** `GET /mermas/{id}`. */
  obtener(id: number): Promise<Merma>;
  /** Alias de `obtener` (sdd/modulo-b-aprobaciones-detalle-editar). */
  obtenerPorId(id: number): Promise<Merma>;
  /** `POST /mermas`. */
  crear(datos: NuevaMerma): Promise<Merma>;
  /** `POST /mermas/{id}/confirmar`. */
  confirmar(id: number): Promise<ConfirmacionMerma>;
  /** `POST /mermas/{id}/rechazar`. */
  rechazar(id: number, datos: RechazoMerma): Promise<Merma>;
  /** sdd/modulo-b-aprobaciones-detalle-editar: `PATCH /mermas/{id}`. */
  editar(id: number, body: MermaUpdateBody): Promise<Merma>;
}
