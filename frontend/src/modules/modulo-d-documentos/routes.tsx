// Rutas propias del módulo de documentos (Boletas, Reportes, Notificaciones).
import type { RouteObject } from "react-router-dom";
import { ProtectedRoute } from "../../shared/components/ProtectedRoute";
import Boletas from "./pages/Boletas";
import Notificaciones from "./pages/Notificaciones";
import Reportes from "./pages/Reportes";

export const rutasModuloD: RouteObject[] = [
  { path: "boletas", element: <Boletas /> },
  {
    path: "reportes",
    element: (
      <ProtectedRoute soloAdmin>
        <Reportes />
      </ProtectedRoute>
    ),
  },
  { path: "notificaciones", element: <Notificaciones /> },
];
