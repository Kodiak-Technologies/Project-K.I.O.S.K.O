// sdd/modulo-b-aprobaciones-detalle-editar: editable form for SolicitudIngreso
// (cabecera + lineas). Mirror del patrón de FormularioProveedor.
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Alert, Button, Input } from "../../../shared/components/ui";
import { SelectorProducto } from "./SelectorProducto";
import { SelectorCategoria } from "./SelectorCategoria";
import { precioVentaSugerido } from "../lib/precios";
import { useMargenDefault } from "../hooks/useMargenDefault";
import type {
  DetalleSolicitud,
  SolicitudIngreso,
  SolicitudIngresoUpdateBody,
} from "../types";

interface Props {
  inicial: SolicitudIngreso;
  onSubmit: (body: SolicitudIngresoUpdateBody) => Promise<void> | void;
  onCancel: () => void;
  /** Si ya está enviando (spinner). */
  procesando?: boolean;
  /** Error a mostrar (ej. response 422). */
  error?: string | null;
}

/** Una línea del formulario.
 *
 *  `esNuevo` decide de dónde sale el producto: del catálogo (`producto_id`) o
 *  de los campos que el cajero escribe a mano. Esto último es lo que le evita
 *  tener que pedirle a un ADMIN que cree el producto antes de poder cargar la
 *  boleta; el alta real ocurre cuando se aprueba.
 *
 *  `precio_compra_total` es el monto de la línea tal cual la boleta: si 7
 *  esponjas costaron S/ 20, se escribe 20 y nadie divide nada. */
interface LineaLocal {
  esNuevo: boolean;
  producto_id: number | null;
  nuevo_codigo: string;
  nuevo_nombre: string;
  nuevo_categoria_id: number | null;
  cantidad: number;
  precio_compra_total: number;
  margen_ganancia: number | null;
}

const LINEA_VACIA: LineaLocal = {
  esNuevo: false,
  producto_id: null,
  nuevo_codigo: "",
  nuevo_nombre: "",
  nuevo_categoria_id: null,
  cantidad: 1,
  precio_compra_total: 0,
  margen_ganancia: null,
};

/** Costo por unidad, solo para mostrar. La fuente de verdad es el total. */
function costoUnitario(l: LineaLocal): number {
  return l.cantidad > 0 ? l.precio_compra_total / l.cantidad : 0;
}

function aLineaLocal(l: DetalleSolicitud): LineaLocal {
  return {
    esNuevo: l.es_producto_nuevo,
    producto_id: l.producto_id,
    nuevo_codigo: l.nuevo_codigo ?? "",
    nuevo_nombre: l.nuevo_nombre ?? "",
    nuevo_categoria_id: l.nuevo_categoria_id,
    cantidad: l.cantidad,
    precio_compra_total: l.precio_compra_total,
    margen_ganancia: l.margen_ganancia,
  };
}

export function FormularioIngresoEditable({
  inicial,
  onSubmit,
  onCancel,
  procesando,
  error,
}: Props) {
  const [motivo, setMotivo] = useState(inicial.motivo ?? "");
  const [lineas, setLineas] = useState<LineaLocal[]>(inicial.lineas.map(aLineaLocal));
  const margenDefault = useMargenDefault();

  // Resync si cambia la solicitud inicial (p. ej. tras recargar)
  useEffect(() => {
    setMotivo(inicial.motivo ?? "");
    setLineas(inicial.lineas.map(aLineaLocal));
  }, [inicial]);

  const cantidadTotal = lineas.reduce((acc, l) => acc + (l.cantidad || 0), 0);
  // Suma de los totales de línea: son lo que dice la boleta. Multiplicar por
  // cantidad acá daría un monto inventado.
  const montoTotal = lineas.reduce((acc, l) => acc + (l.precio_compra_total || 0), 0);

  function agregarLinea() {
    setLineas((prev) => [...prev, { ...LINEA_VACIA }]);
  }
  function quitarLinea(idx: number) {
    setLineas((prev) => prev.filter((_, i) => i !== idx));
  }
  function actualizarLinea(idx: number, patch: Partial<LineaLocal>) {
    setLineas((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  }

  function validar(): string | null {
    const codigosNuevos = new Set<string>();
    for (let i = 0; i < lineas.length; i++) {
      const l = lineas[i];
      if (l.esNuevo) {
        const codigo = l.nuevo_codigo.trim();
        if (!codigo) return `Línea ${i + 1}: falta el código de barras.`;
        if (!l.nuevo_nombre.trim()) return `Línea ${i + 1}: falta el nombre del producto.`;
        if (codigosNuevos.has(codigo))
          return `Línea ${i + 1}: el código ${codigo} está repetido.`;
        codigosNuevos.add(codigo);
      } else if (!l.producto_id) {
        return `Línea ${i + 1}: selecciona un producto.`;
      }
      if (l.cantidad <= 0) return `Línea ${i + 1}: la cantidad debe ser > 0.`;
      if (l.precio_compra_total < 0)
        return `Línea ${i + 1}: el total no puede ser negativo.`;
    }
    return null;
  }

  const errorValidacion = validar();

  async function manejarSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (errorValidacion) return;
    const body: SolicitudIngresoUpdateBody = {
      motivo: motivo.trim() === "" ? null : motivo.trim(),
      lineas: lineas.map((l) => ({
        cantidad: l.cantidad,
        precio_compra_total: l.precio_compra_total,
        // Se manda uno u otro, nunca los dos: el backend valida lo mismo.
        producto_id: l.esNuevo ? null : l.producto_id,
        nuevo_codigo: l.esNuevo ? l.nuevo_codigo.trim() : null,
        nuevo_nombre: l.esNuevo ? l.nuevo_nombre.trim() : null,
        nuevo_categoria_id: l.esNuevo ? l.nuevo_categoria_id : null,
        margen_ganancia: l.esNuevo ? l.margen_ganancia : null,
      })),
    };
    await onSubmit(body);
  }

  return (
    <form onSubmit={manejarSubmit} className="space-y-4">
      <Input
        label="Motivo (opcional)"
        placeholder="ej. corrección de proveedor"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        maxLength={500}
      />

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-zinc-800">Líneas</h4>
          <Button type="button" compacto variante="secundario" onClick={agregarLinea}>
            <Plus className="mr-1 h-4 w-4" /> Agregar línea
          </Button>
        </div>
        <div className="overflow-hidden rounded-lg border border-zinc-200">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
              <tr>
                <th className="px-3 py-2 text-left">Producto</th>
                <th className="px-3 py-2 text-right">Cantidad</th>
                {/* Total, no unitario: la solicitud transcribe la boleta. */}
                <th className="px-3 py-2 text-right">Total boleta</th>
                <th className="px-3 py-2 text-right">Costo unit.</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {lineas.map((l, i) => (
                <tr key={i} className="border-t border-zinc-100">
                  <td className="px-3 py-2">
                    <div className="space-y-1.5">
                      {l.esNuevo ? (
                        <>
                          <input
                            type="text"
                            placeholder="Código de barras"
                            className="w-full rounded border border-zinc-200 px-2 py-1"
                            value={l.nuevo_codigo}
                            maxLength={60}
                            onChange={(e) =>
                              actualizarLinea(i, { nuevo_codigo: e.target.value })
                            }
                          />
                          <input
                            type="text"
                            placeholder="Nombre del producto"
                            className="w-full rounded border border-zinc-200 px-2 py-1"
                            value={l.nuevo_nombre}
                            maxLength={150}
                            onChange={(e) =>
                              actualizarLinea(i, { nuevo_nombre: e.target.value })
                            }
                          />
                          <SelectorCategoria
                            value={l.nuevo_categoria_id}
                            onChange={(id) =>
                              actualizarLinea(i, { nuevo_categoria_id: id })
                            }
                          />
                        </>
                      ) : (
                        <SelectorProducto
                          value={l.producto_id}
                          onChange={(id) => actualizarLinea(i, { producto_id: id })}
                        />
                      )}
                      <button
                        type="button"
                        className="text-xs text-primario hover:underline"
                        onClick={() =>
                          actualizarLinea(i, {
                            esNuevo: !l.esNuevo,
                            producto_id: null,
                            nuevo_codigo: "",
                            nuevo_nombre: "",
                            nuevo_categoria_id: null,
                          })
                        }
                      >
                        {l.esNuevo
                          ? "Elegir del catálogo"
                          : "No está en el catálogo — crearlo"}
                      </button>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      min={1}
                      className="w-20 rounded border border-zinc-200 px-2 py-1 text-right tabular-nums"
                      value={l.cantidad}
                      onChange={(e) =>
                        actualizarLinea(i, { cantidad: Math.max(1, Number(e.target.value) || 1) })
                      }
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      className="w-24 rounded border border-zinc-200 px-2 py-1 text-right tabular-nums"
                      value={l.precio_compra_total}
                      onChange={(e) =>
                        actualizarLinea(i, {
                          precio_compra_total: Math.max(0, Number(e.target.value) || 0),
                        })
                      }
                    />
                    {l.esNuevo && (
                      <>
                        <div className="mt-1.5 flex items-center justify-end gap-1 text-xs text-zinc-500">
                          <span>Margen</span>
                          <input
                            type="number"
                            min={0}
                            step={1}
                            placeholder={String(margenDefault)}
                            className="w-14 rounded border border-zinc-200 px-1 py-0.5 text-right tabular-nums"
                            value={l.margen_ganancia ?? ""}
                            onChange={(e) =>
                              actualizarLinea(i, {
                                margen_ganancia:
                                  e.target.value === ""
                                    ? null
                                    : Math.max(0, Number(e.target.value) || 0),
                              })
                            }
                          />
                          <span>%</span>
                        </div>
                        {/* Con qué precio queda el producto en el catálogo.
                            Es la decisión que se está tomando al aprobar. */}
                        {l.precio_compra_total > 0 && l.cantidad > 0 && (
                          <div className="mt-1 text-right text-xs text-emerald-800">
                            Venta: S/{" "}
                            <strong className="tabular-nums">
                              {precioVentaSugerido(
                                l.precio_compra_total,
                                l.cantidad,
                                l.margen_ganancia ?? margenDefault,
                              ).toFixed(2)}
                            </strong>
                          </div>
                        )}
                      </>
                    )}
                  </td>
                  {/* Derivado: se muestra para control, no se edita. */}
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-500">
                    {costoUnitario(l).toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => quitarLinea(i)}
                      aria-label="Quitar línea"
                      className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-peligro"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {lineas.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-center text-xs text-zinc-500">
                    Sin líneas. Agrega al menos una para guardar.
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot className="bg-zinc-50">
              <tr>
                <td className="px-3 py-2 text-right text-xs text-zinc-500" colSpan={1}>
                  Totales
                </td>
                <td className="px-3 py-2 text-right text-sm font-medium tabular-nums">
                  {cantidadTotal}
                </td>
                <td className="px-3 py-2 text-right text-sm font-medium tabular-nums">
                  S/ {montoTotal.toFixed(2)}
                </td>
                <td className="px-3 py-2" />
                <td className="px-3 py-2" />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {errorValidacion && <Alert tono="alerta">{errorValidacion}</Alert>}
      {error && <Alert tono="peligro">{error}</Alert>}

      <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
        <Button type="button" variante="secundario" onClick={onCancel} disabled={procesando}>
          Cancelar
        </Button>
        <Button
          type="submit"
          cargando={procesando}
          disabled={lineas.length === 0 || errorValidacion !== null}
        >
          Guardar cambios
        </Button>
      </div>
    </form>
  );
}
