// Una línea del formulario de Ingresos de mercadería.
// Reutilizado en IngresosMercaderia (N líneas dinámicas).
//
// Dos cosas que no son obvias y conviene tener presentes:
//
//   1. El precio que se pide es el TOTAL de la línea, no el unitario. La
//      solicitud es una transcripción de la boleta: si 7 esponjas costaron
//      S/ 20, se escribe 20. Pedir el unitario obligaba al cajero a dividir
//      (y 20/7 ni siquiera da exacto).
//   2. El producto puede no existir todavía en el catálogo. En ese caso el
//      cajero escribe código, nombre y categoría acá mismo, sin depender de
//      que un ADMIN lo dé de alta primero. El producto se crea al aprobar.
import { Trash2 } from "lucide-react";
import { Input } from "../../../shared/components/ui";
import { SelectorProducto } from "./SelectorProducto";
import { SelectorCategoria } from "./SelectorCategoria";

export interface LineaIngreso {
  /** true = producto a crear; false = producto del catálogo. */
  esNuevo: boolean;
  /** `null` = aún no elegido. Solo se usa si `esNuevo` es false. */
  producto_id: number | null;
  /** Campos del producto propuesto. Solo se usan si `esNuevo` es true. */
  nuevo_codigo: string;
  nuevo_nombre: string;
  nuevo_categoria_id: number | null;
  cantidad: number;
  /** Monto de la línea tal cual la boleta. */
  precio_compra_total: number;
  /** % de ganancia. `null` = usar el del negocio. */
  margen_ganancia: number | null;
}

export const LINEA_INGRESO_VACIA: LineaIngreso = {
  esNuevo: false,
  producto_id: null,
  nuevo_codigo: "",
  nuevo_nombre: "",
  nuevo_categoria_id: null,
  cantidad: 1,
  precio_compra_total: 0,
  margen_ganancia: null,
};

interface Props {
  linea: LineaIngreso;
  /** Errores de validación de la línea. */
  errores?: {
    producto_id?: string;
    cantidad?: string;
    precio_compra_total?: string;
    nuevo_codigo?: string;
    nuevo_nombre?: string;
  };
  /** Si es la única línea, no se puede eliminar. */
  esUnica: boolean;
  onChange: (linea: LineaIngreso) => void;
  onEliminar: () => void;
}

export function FormularioLineaIngreso({
  linea,
  errores,
  esUnica,
  onChange,
  onEliminar,
}: Props) {
  const costoUnitario =
    linea.cantidad > 0 ? linea.precio_compra_total / linea.cantidad : 0;

  function alternarModo() {
    // Limpiar ambos lados al cambiar: dejar residuos del modo anterior
    // mandaría al backend una línea que dice ser dos cosas a la vez.
    onChange({
      ...linea,
      esNuevo: !linea.esNuevo,
      producto_id: null,
      nuevo_codigo: "",
      nuevo_nombre: "",
      nuevo_categoria_id: null,
      margen_ganancia: null,
    });
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          Línea{linea.esNuevo && " · producto nuevo"}
        </span>
        {!esUnica && (
          <button
            type="button"
            onClick={onEliminar}
            aria-label="Eliminar línea"
            className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-peligro"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_6rem] lg:grid-cols-[1fr_6rem_9rem]">
        {linea.esNuevo ? (
          <div className="space-y-2">
            <Input
              label="Código de barras"
              requerido
              maxLength={60}
              placeholder="Escanealo o escribilo"
              value={linea.nuevo_codigo}
              onChange={(e) => onChange({ ...linea, nuevo_codigo: e.target.value })}
              error={errores?.nuevo_codigo}
            />
            <Input
              label="Nombre del producto"
              requerido
              maxLength={150}
              value={linea.nuevo_nombre}
              onChange={(e) => onChange({ ...linea, nuevo_nombre: e.target.value })}
              error={errores?.nuevo_nombre}
            />
            <div>
              <span className="mb-1 block text-sm font-medium text-zinc-700">
                Categoría
              </span>
              <SelectorCategoria
                value={linea.nuevo_categoria_id}
                onChange={(id) => onChange({ ...linea, nuevo_categoria_id: id })}
              />
            </div>
          </div>
        ) : (
          /* Búsqueda contra el servidor: el catálogo puede tener miles de SKUs
             y traerlo entero rompía la pantalla al pasar el tope de la API. */
          <SelectorProducto
            label="Producto"
            requerido
            value={linea.producto_id}
            onChange={(id) => onChange({ ...linea, producto_id: id })}
            error={errores?.producto_id}
          />
        )}

        <Input
          label="Cantidad"
          type="number"
          min={1}
          requerido
          value={linea.cantidad || ""}
          onChange={(e) => onChange({ ...linea, cantidad: Number(e.target.value) })}
          error={errores?.cantidad}
        />

        <div className="space-y-1">
          <Input
            label="Total boleta (S/)"
            type="number"
            step="0.01"
            min={0}
            requerido
            value={linea.precio_compra_total || ""}
            onChange={(e) =>
              onChange({ ...linea, precio_compra_total: Number(e.target.value) })
            }
            error={errores?.precio_compra_total}
          />
          {linea.cantidad > 0 && linea.precio_compra_total > 0 && (
            <p className="text-xs text-zinc-500 tabular-nums">
              S/ {costoUnitario.toFixed(2)} c/u
            </p>
          )}
          {linea.esNuevo && (
            <Input
              label="Margen (%)"
              type="number"
              min={0}
              step="1"
              placeholder="Por defecto del negocio"
              value={linea.margen_ganancia ?? ""}
              onChange={(e) =>
                onChange({
                  ...linea,
                  margen_ganancia: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={alternarModo}
        className="mt-2 text-xs text-primario hover:underline"
      >
        {linea.esNuevo
          ? "← Elegir un producto del catálogo"
          : "El producto no está en el catálogo — crearlo desde acá"}
      </button>
    </div>
  );
}
