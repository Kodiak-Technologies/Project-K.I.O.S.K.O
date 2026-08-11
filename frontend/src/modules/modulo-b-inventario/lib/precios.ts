// Espejo de `backend/app/modules/modulo_b_inventario/domain/precios.py`.
//
// Solo deriva el costo por unidad a partir del total de la línea, que es lo que
// dice la boleta ("7 esponjas — S/ 20"). No hay cálculo de precio de venta: el
// ingreso no fija precios de catálogo (antes lo hacía con un margen sobre el
// costo, y terminaba cambiando el precio del punto de venta sin decisión de
// nadie). El precio de venta se administra desde el catálogo.

/** Costo por unidad derivado del total de la línea. */
export function costoUnitario(precioCompraTotal: number, cantidad: number): number {
  if (cantidad <= 0) return 0;
  return precioCompraTotal / cantidad;
}
