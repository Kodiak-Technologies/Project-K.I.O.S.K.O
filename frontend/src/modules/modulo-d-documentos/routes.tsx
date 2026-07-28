import type { RouteObject } from "react-router-dom";
import { ProtectedRoute } from "../../shared/components/ProtectedRoute";
import NotasDeVenta from "./pages/NotasDeVenta";
import Notificaciones from "./pages/Notificaciones";
import Reportes from "./pages/Reportes";
import Respaldos from "./pages/Respaldos";

export const rutasModuloD: RouteObject[] = [
  { path: "notas-venta", element: <NotasDeVenta /> },
  { path: "boletas", element: <NotasDeVenta /> },
  {
    path: "reportes",
    element: (
      <ProtectedRoute soloAdmin>
        <Reportes />
      </ProtectedRoute>
    ),
  },
  { path: "notificaciones", element: <Notificaciones /> },
  {
    path: "respaldos",
    element: (
      <ProtectedRoute soloAdmin>
        <Respaldos />
      </ProtectedRoute>
    ),
  },
];
