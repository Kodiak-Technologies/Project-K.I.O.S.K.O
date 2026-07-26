// Rutas propias del módulo de inventario (Catalogo, IngresosMercaderia,
// AprobacionIngresos, Proveedores, ProveedorDetalle, MovimientosInventario).
//
// El catálogo de CONSULTA (solo lectura) vive en el punto de venta; esta vista
// es la de gestión y por eso es solo para ADMIN.
import { Navigate, type RouteObject } from "react-router-dom";
import { ProtectedRoute } from "../../shared/components/ProtectedRoute";
import AprobacionIngresos from "./pages/AprobacionIngresos";
import Catalogo from "./pages/Catalogo";
import IngresosMercaderia from "./pages/IngresosMercaderia";
import MovimientosInventario from "./pages/MovimientosInventario";
import ProveedorDetalle from "./pages/ProveedorDetalle";
import Proveedores from "./pages/Proveedores";

export const rutasModuloB: RouteObject[] = [
  {
    path: "catalogo",
    element: (
      <ProtectedRoute soloAdmin>
        <Catalogo />
      </ProtectedRoute>
    ),
  },
  // La antigua "Productos+" se fusionó con el catálogo: los enlaces viejos siguen andando.
  { path: "productos", element: <Navigate to="/catalogo" replace /> },
  { path: "ingresos", element: <IngresosMercaderia /> },
  {
    path: "aprobaciones",
    element: (
      <ProtectedRoute soloAdmin>
        <AprobacionIngresos />
      </ProtectedRoute>
    ),
  },
  // Proveedores (admin-only: alta, edición, deudas).
  {
    path: "proveedores",
    element: (
      <ProtectedRoute soloAdmin>
        <Proveedores />
      </ProtectedRoute>
    ),
  },
  {
    path: "proveedores/:id",
    element: (
      <ProtectedRoute soloAdmin>
        <ProveedorDetalle />
      </ProtectedRoute>
    ),
  },
  // Bitácora pública para ADMIN y CAJERO.
  { path: "movimientos", element: <MovimientosInventario /> },
];
