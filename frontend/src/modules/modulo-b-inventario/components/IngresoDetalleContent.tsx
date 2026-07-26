// sdd/modulo-b-aprobaciones-detalle-editar: read-only detail layout for
// SolicitudIngreso. Refactor del cuerpo del modal inline en
// AprobacionIngresos.tsx (líneas 211-302). Ahora reutilizable y con el
// botón "Editar" gated por `canEditIngreso`.
import { Pencil } from "lucide-react";
import { Button } from "../../../shared/components/ui";
import { canEditIngreso } from "../lib/permisos";
import type { Producto, SolicitudIngreso } from "../types";

interface UsuarioMin {
  id: number;
  rol: string;
  nombre: string;
}

interface Props {
  ingreso: SolicitudIngreso;
  currentUser: UsuarioMin | null;
  productos: Producto[];
  onEditarClick: () => void;
}

export function IngresoDetalleContent({
  ingreso,
  currentUser,
  productos,
  onEditarClick,
}: Props) {
  const puedeEditar = canEditIngreso(ingreso, currentUser);
  const nombreProducto = (id: number) =>
    productos.find((p) => p.id === id)?.nombre ?? `#${id}`;

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
        {ingreso.monto_total != null && (
          <div>
            <dt className="text-zinc-500">Monto total</dt>
            <dd>S/ {ingreso.monto_total.toFixed(2)}</dd>
          </div>
        )}
        {ingreso.motivo != null && (
          <div className="sm:col-span-2">
            <dt className="text-zinc-500">Motivo</dt>
            <dd>{ingreso.motivo}</dd>
          </div>
        )}
        {ingreso.editado_en != null && (
          <div className="sm:col-span-2 text-xs text-zinc-500">
            Editado por {ingreso.editado_por_nombre} el{" "}
            {new Date(ingreso.editado_en).toLocaleString("es-PE")}
          </div>
        )}
      </dl>
      {ingreso.foto_boleta_url && (
        <a href={ingreso.foto_boleta_url} target="_blank" rel="noopener noreferrer">
          <img
            src={ingreso.foto_boleta_url}
            alt="Boleta"
            className="max-h-64 rounded-lg border border-zinc-200 object-contain"
          />
        </a>
      )}
      <div>
        <h4 className="mb-2 text-sm font-semibold text-zinc-800">Líneas</h4>
        <ul className="divide-y divide-zinc-100 rounded-lg border border-zinc-200">
          {ingreso.lineas.map((l) => (
            <li key={l.id} className="flex items-center justify-between px-3 py-2 text-sm">
              <span className="truncate">{nombreProducto(l.producto_id)}</span>
              <span className="ml-3 shrink-0 tabular-nums text-zinc-500">
                {l.cantidad} × S/ {l.precio_compra_unitario.toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
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
