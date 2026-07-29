// Espejo de `backend/app/modules/modulo_b_inventario/domain/precios.py`.
//
// Existe para que el formulario de ingresos pueda mostrar, ANTES de enviar, el
// precio de venta con el que va a quedar el producto en el catálogo. Es una
// previsualización: la que manda es la del backend, que recalcula al aprobar.
//
// Si cambia la regla de redondeo, hay que tocar los dos archivos. El backend es
// la fuente de verdad; este es el que se adapta.

/** Granularidad del precio de venta de cara al público (S/ 0.10). */
export const PASO_PRECIO_VENTA = 0.1;

/** Costo por unidad derivado del total de la línea. */
export function costoUnitario(precioCompraTotal: number, cantidad: number): number {
  if (cantidad <= 0) return 0;
  return precioCompraTotal / cantidad;
}

/**
 * Precio de venta unitario aplicando el margen, redondeado hacia arriba al
 * siguiente múltiplo de 0.10.
 *
 * Ejemplo: 7 esponjas a S/ 20 con 20% → 2.857… × 1.20 = 3.428… → 3.50
 *
 * El margen se aplica sobre el unitario exacto (sin redondear antes) para no
 * arrastrar el error de redondeo al precio final.
 */
export function precioVentaSugerido(
  precioCompraTotal: number,
  cantidad: number,
  margenPorcentaje: number,
): number {
  if (cantidad <= 0) return 0;
  const conMargen = (precioCompraTotal / cantidad) * (1 + margenPorcentaje / 100);
  // `toFixed(4)` antes de dividir: sin eso, 3.4285…/0.1 da 34.285000000000004
  // y en los casos que caen justo sobre el múltiplo Math.ceil sube un paso de
  // más (ej. 3.30 → 3.40).
  const pasos = Math.ceil(Number((conMargen / PASO_PRECIO_VENTA).toFixed(4)));
  return Number((pasos * PASO_PRECIO_VENTA).toFixed(2));
}
