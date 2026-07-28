// Rutas propias del módulo de seguridad. App.tsx las monta en el router raíz.
import type { RouteObject } from "react-router-dom";
import { ProtectedRoute } from "../../shared/components/ProtectedRoute";
import Bitacora from "./pages/Bitacora";
import Configuracion from "./pages/Configuracion";
import GestionUsuarios from "./pages/GestionUsuarios";

// Login se registra aparte en App.tsx porque vive FUERA del Layout autenticado.
export const rutasModuloA: RouteObject[] = [
  {
    path: "usuarios",
    element: (
      <ProtectedRoute soloAdmin>
        <GestionUsuarios />
      </ProtectedRoute>
    ),
  },
  {
    path: "bitacora",
    element: (
      <ProtectedRoute soloAdmin>
        <Bitacora />
      </ProtectedRoute>
    ),
  },
  {
    path: "configuracion",
    element: (
      <ProtectedRoute soloAdmin>
        <Configuracion />
      </ProtectedRoute>
    ),
  },
];
