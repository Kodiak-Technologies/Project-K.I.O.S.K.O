// Rutas propias del módulo de ventas (PuntoDeVenta, HistorialVentas, AperturaCaja, CierreCaja, Fiados).
import type { RouteObject } from "react-router-dom";
import AperturaCaja from "./pages/AperturaCaja";
import CierreCaja from "./pages/CierreCaja";
import Fiados from "./pages/Fiados";
import HistorialVentas from "./pages/HistorialVentas";
import PuntoDeVenta from "./pages/PuntoDeVenta";

export const rutasModuloC: RouteObject[] = [
  { path: "pos", element: <PuntoDeVenta /> },
  { path: "caja", element: <AperturaCaja /> },
  { path: "caja/cierre", element: <CierreCaja /> },
  { path: "historial-ventas", element: <HistorialVentas /> },
  { path: "fiados", element: <Fiados /> },
];
