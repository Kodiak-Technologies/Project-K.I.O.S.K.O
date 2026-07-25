// sdd/modulo-b-aprobaciones-detalle-editar: central permission gate helpers.
// Mirrors the use case rule (FR-3.1 / FR-4.1):
//   - estado editable (Pendiente / Registrada)
//   - ADMIN OR row creator
// Returns `false` (not throw) for downstream UI to gate the "Editar" button.
import type { Merma, SolicitudIngreso } from "../types";

// Re-declare a minimal Usuario shape so this file doesn't depend on the
// modulo-a-seguridad types (kept narrow to avoid cycles).
interface UsuarioMin {
  id: number;
  rol: string;
}

export function canEditIngreso(
  s: SolicitudIngreso,
  currentUser: UsuarioMin | null,
): boolean {
  if (!currentUser) return false;
  if (s.estado !== "Pendiente") return false;
  return currentUser.rol === "ADMIN" || s.solicitado_por === currentUser.id;
}

export function canEditMerma(
  m: Merma,
  currentUser: UsuarioMin | null,
): boolean {
  if (!currentUser) return false;
  if (m.estado !== "Registrada") return false;
  return currentUser.rol === "ADMIN" || m.registrado_por === currentUser.id;
}
