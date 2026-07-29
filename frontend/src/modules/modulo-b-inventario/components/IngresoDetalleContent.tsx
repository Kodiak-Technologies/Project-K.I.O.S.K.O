// Detalle de solo lectura de una SolicitudIngreso: datos de cabecera + la lista
// de productos a ingresar (cantidad y costo unitario) con su total.
//
// NO incluye la boleta: en la pantalla de aprobaciones la boleta va en la
// columna de la derecha, al lado de esta lista, para poder compararlas.
import { Pencil } from "lucide-react";
import { Button } from "../../../shared/components/ui";
import { canEditIngreso } from "../lib/permisos";
import type { SolicitudIngreso } from "../types";

interface UsuarioMin {
  id: number;
  rol: string;
  nombre: string;
}

interface Props {
  ingreso: SolicitudIngreso;
  currentUser: UsuarioMin | null;
  onEditarClick: () => void;
}

export function IngresoDetalleContent({
  ingreso,
  currentUser,
  onEditarClick,
}: Props) {
  const puedeEditar = canEditIngreso(ingreso, currentUser);
  // Suma de totales de línea: son el dato de la boleta. Reconstruirlos como
  // cantidad × unitario redondeado descuadraría contra lo que se pagó.
  const total =
    ingreso.monto_total ??
    ingreso.lineas.reduce((suma, l) => suma + l.precio_compra_total, 0);
  const unidades = ingreso.lineas.reduce((suma, l) => suma + l.cantidad, 0);

  return (
    <div className="space-y-4">
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-zinc-500">Fecha</dt>
          <dd>
            {ingreso.created_at ? new Date(ingreso.created_at).toLocaleString("es-PE") : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Solicitado por</dt>
          <dd>{ingreso.solicitado_por_nombre}</dd>
        </div>
        {ingreso.proveedor_id != null && (
          <div>
            <dt className="text-zinc-500">Proveedor</dt>
            <dd>#{ingreso.proveedor_id}</dd>
          </div>
        )}
        {ingreso.motivo != null && (
          <div className="sm:col-span-2">
            <dt className="text-zinc-500">Motivo</dt>
            <dd>{ingreso.motivo}</dd>
          </div>
        )}
        {ingreso.editado_en != null && (
          <div className="text-xs text-zinc-500 sm:col-span-2">
            Editado por {ingreso.editado_por_nombre} el{" "}
            {new Date(ingreso.editado_en).toLocaleString("es-PE")}
          </div>
        )}
      </dl>

      {/* Productos a ingresar: es lo que hay que contrastar contra la boleta. */}
      <div>
        <h4 className="mb-2 text-sm font-semibold text-zinc-800">
          Productos por ingresar ({ingreso.lineas.length})
        </h4>
        <div className="overflow-x-auto rounded-lg border border-zinc-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 text-left text-[11px] uppercase text-zinc-500">
                <th className="px-3 py-2 font-medium">Producto</th>
                <th className="px-3 py-2 text-right font-medium">Cantidad</th>
                <th className="px-3 py-2 text-right font-medium">Costo unit.</th>
                <th className="px-3 py-2 text-right font-medium">Total boleta</th>
              </tr>
            </thead>
            <tbody>
              {ingreso.lineas.map((l) => (
                <tr key={l.id} className="border-b border-zinc-100 last:border-0">
                  <td className="px-3 py-2">
                    <span className="block truncate text-zinc-800">
                      {l.producto_nombre ?? l.nuevo_nombre ?? `#${l.producto_id}`}
                    </span>
                    {(l.producto_codigo ?? l.nuevo_codigo) && (
                      <span className="font-mono text-xs text-zinc-400">
                        {l.producto_codigo ?? l.nuevo_codigo}
                      </span>
                    )}
                    {l.es_producto_nuevo && (
                      <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
                        se creará al aprobar
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{l.cantidad}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-500">
                    S/ {l.precio_compra_unitario.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right font-medium tabular-nums">
                    S/ {l.precio_compra_total.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-zinc-200 bg-zinc-50">
                <td className="px-3 py-2 text-xs uppercase text-zinc-500">Total</td>
                <td className="px-3 py-2 text-right font-medium tabular-nums">{unidades}</td>
                <td />
                <td className="px-3 py-2 text-right font-semibold tabular-nums">
                  S/ {total.toFixed(2)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* FR-7.8: el botón "Editar" se OCULTA (no se deshabilita) cuando el
          gate falla — no revelamos editabilidad a quien no puede actuar. */}
      {puedeEditar && (
        <div className="flex justify-end">
          <Button onClick={onEditarClick} icono={<Pencil className="h-4 w-4" aria-hidden />}>
            Editar
          </Button>
        </div>
      )}
    </div>
  );
}
