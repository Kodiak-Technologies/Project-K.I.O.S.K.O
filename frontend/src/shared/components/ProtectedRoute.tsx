// Guarda de rutas: exige sesión activa (y opcionalmente rol ADMIN).
// La seguridad REAL la valida el backend; esto solo mejora la experiencia de uso.
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuthContext } from "../lib/auth-context";

export function ProtectedRoute({ children, soloAdmin = false }: { children: ReactNode; soloAdmin?: boolean }) {
  const { usuario, cargando } = useAuthContext();

  if (cargando) {
    return <div className="flex min-h-screen items-center justify-center text-gray-500">Cargando…</div>;
  }
  if (!usuario) return <Navigate to="/login" replace />;
  if (soloAdmin && usuario.rol !== "ADMIN") return <Navigate to="/" replace />;
  return <>{children}</>;
}
