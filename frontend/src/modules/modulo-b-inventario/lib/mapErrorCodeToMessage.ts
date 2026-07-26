// sdd/modulo-b-aprobaciones-detalle-editar: error code → user-friendly message.
// Centraliza el mapping (NFR-5 / FR-7.5) para que las páginas no
// dupliquen strings de UX.
import type { ErrorCodeBackend } from "../types";

const MAP: Record<ErrorCodeBackend, string> = {
  EMPTY_PATCH: "No hay cambios para guardar.",
  NOT_EDITABLE_STATE: "Esta solicitud ya no se puede editar (cambió de estado). Refrescá la lista.",
  FORBIDDEN: "No tenés permiso para editar esta solicitud.",
  PRODUCT_NOT_FOUND: "Uno de los productos seleccionados no existe.",
  PROVEEDOR_NOT_FOUND: "El proveedor seleccionado no existe.",
  INVALID_LINE_VALUES: "Revisá las cantidades y precios de las líneas.",
  INVALID_CANTIDAD: "La cantidad debe ser mayor a 0.",
  INVALID_MOTIVO: "El motivo indicado no es válido.",
  STOCK_INSUFICIENTE: "No hay stock suficiente para descontar esa cantidad.",
  MOTIVO_REQUERIDO: "Indicá el motivo del ajuste (mínimo 3 caracteres).",
  UNKNOWN_FIELD: "El formulario envió campos no permitidos. Recargá la página.",
  CONCURRENT_EDIT: "Otro usuario está editando esta solicitud. Reintentá en unos segundos.",
  INGRESO_NOT_FOUND: "La solicitud no existe o fue eliminada.",
  ALREADY_REJECTED: "Esta solicitud ya fue rechazada.",
  MOTIVO_RECHAZO_TOO_SHORT: "El motivo debe tener al menos 5 caracteres.",
};

export function mapErrorCodeToMessage(code: string | undefined): string {
  if (code && code in MAP) {
    return MAP[code as ErrorCodeBackend];
  }
  return "No se pudo guardar. Reintentá.";
}
