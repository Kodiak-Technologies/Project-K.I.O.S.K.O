// sdd/modulo-b-aprobaciones-detalle-editar: read-only detail layout for Merma.
// New: AprobacionMermas previously lacked a "ver detalles" UX.
import { Pencil } from "lucide-react";
import { Button } from "../../../shared/components/ui";
import { canEditMerma } from "../lib/permisos";
import type { Merma, Producto } from "../types";

interface UsuarioMin {
  id: number;
  rol: string;
  nombre: string;
}

interface Props {
  merma: Merma;
  currentUser: UsuarioMin | null;
  productos: Producto[];
  onEditarClick: () => void;
}

const MOTIVO_LABELS: Record<string, string> = {
  vencimiento: "Vencimiento",
  rotura: "Rotura",
  otro: "Otro",
};

export function MermaDetalleContent({ merma, currentUser, productos, onEditarClick }: Props) {
  const puedeEditar = canEditMerma(merma, currentUser);
  const nombreProducto = (id: number) =>
    productos.find((p) => p.id === id)?.nombre ?? `#${id}`;

  return (
    <div className="space-y-4">
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-zinc-500">Fecha</dt>
          <dd>
            {merma.created_at ? new Date(merma.created_at).toLocaleString("es-PE") : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Reportó</dt>
          <dd>{merma.registrado_por_nombre}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Producto</dt>
          <dd>{nombreProducto(merma.producto_id)}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Cantidad</dt>
          <dd className="tabular-nums">{merma.cantidad}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Motivo</dt>
          <dd>{MOTIVO_LABELS[String(merma.motivo)] ?? merma.motivo}</dd>
        </div>
        {merma.proveedor_id != null && (
          <div>
            <dt className="text-zinc-500">Proveedor</dt>
            <dd>#{merma.proveedor_id}</dd>
          </div>
        )}
        <div className="sm:col-span-2">
          <dt className="text-zinc-500">Observación</dt>
          <dd>{merma.observacion || "—"}</dd>
        </div>
        {merma.editado_en != null && (
          <div className="sm:col-span-2 text-xs text-zinc-500">
            Editado por {merma.editado_por_nombre} el{" "}
            {new Date(merma.editado_en).toLocaleString("es-PE")}
          </div>
        )}
      </dl>

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
