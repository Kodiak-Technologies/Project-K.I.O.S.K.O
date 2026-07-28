// Guarda de rutas: exige sesión activa (y opcionalmente rol ADMIN).
// La seguridad REAL la valida el backend; esto solo mejora la experiencia de uso.
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthContext } from "../lib/auth-context";

export function ProtectedRoute({ children, soloAdmin = false }: { children: ReactNode; soloAdmin?: boolean }) {
  const { usuario, cargando } = useAuthContext();
  const ubicacion = useLocation();

  if (cargando) {
    return <div className="flex min-h-screen items-center justify-center text-zinc-500">Cargando…</div>;
  }
  if (!usuario) return <Navigate to="/login" replace />;
  // Contraseña temporal (usuario nuevo o reseteado): no puede usar el sistema
  // hasta cambiarla. Se le redirige SIEMPRE a la pantalla de cambio.
  if (usuario.debe_cambiar_password && ubicacion.pathname !== "/cambiar-password") {
    return <Navigate to="/cambiar-password" replace />;
  }
  if (soloAdmin && usuario.rol !== "ADMIN") return <Navigate to="/" replace />;
  return <>{children}</>;
}
