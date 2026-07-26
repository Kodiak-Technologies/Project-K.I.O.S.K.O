// Rutas propias del módulo de inventario (Catalogo, GestionProductos, IngresosMercaderia,
// AprobacionIngresos, Mermas, AprobacionMermas, Proveedores, ProveedorDetalle, MovimientosInventario).
import type { RouteObject } from "react-router-dom";
import { ProtectedRoute } from "../../shared/components/ProtectedRoute";
import AprobacionIngresos from "./pages/AprobacionIngresos";
import AprobacionMermas from "./pages/AprobacionMermas";
import Catalogo from "./pages/Catalogo";
import GestionProductos from "./pages/GestionProductos";
import IngresosMercaderia from "./pages/IngresosMercaderia";
import MovimientosInventario from "./pages/MovimientosInventario";
import Mermas from "./pages/Mermas";
import ProveedorDetalle from "./pages/ProveedorDetalle";
import Proveedores from "./pages/Proveedores";

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
  // Mermas: el CAJERO registra (paso 1). El ADMIN ve la cola de confirmación.
  { path: "mermas", element: <Mermas /> },
  {
    path: "mermas/aprobacion",
    element: (
      <ProtectedRoute soloAdmin>
        <AprobacionMermas />
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
