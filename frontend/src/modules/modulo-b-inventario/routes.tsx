// Rutas propias del módulo de inventario (Catalogo, GestionProductos, IngresosMercaderia, AprobacionIngresos).
import type { RouteObject } from "react-router-dom";
import { ProtectedRoute } from "../../shared/components/ProtectedRoute";
import AprobacionIngresos from "./pages/AprobacionIngresos";
import Catalogo from "./pages/Catalogo";
import GestionProductos from "./pages/GestionProductos";
import IngresosMercaderia from "./pages/IngresosMercaderia";

export const rutasModuloB: RouteObject[] = [
  { path: "catalogo", element: <Catalogo /> },
  {
    path: "productos",
    element: (
      <ProtectedRoute soloAdmin>
        <GestionProductos />
      </ProtectedRoute>
    ),
  },
  { path: "ingresos", element: <IngresosMercaderia /> },
  {
    path: "aprobaciones",
    element: (
      <ProtectedRoute soloAdmin>
        <AprobacionIngresos />
      </ProtectedRoute>
    ),
  },
];
