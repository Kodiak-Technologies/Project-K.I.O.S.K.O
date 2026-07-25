// sdd/modulo-b-aprobaciones-detalle-editar: editable form for Merma.
// Single-product, motivo select, observacion textarea, proveedor select. No lineas.
import { useEffect, useState } from "react";
import { Alert, Button, Input, Select } from "../../../shared/components/ui";
import { useProveedores } from "../hooks/useProveedores";
import { SelectorProducto } from "./SelectorProducto";
import type { Merma, MermaUpdateBody, MotivoMerma } from "../types";

interface Props {
  inicial: Merma;
  onSubmit: (body: MermaUpdateBody) => Promise<void> | void;
  onCancel: () => void;
  procesando?: boolean;
  error?: string | null;
}

export function FormularioMermaEditable({
  inicial,
  onSubmit,
  onCancel,
  procesando,
  error,
}: Props) {
  // sdd/modulo-b-aprobaciones-detalle-editar (verify fix #6): el form ahora
  // expone `proveedor_id` para que el usuario pueda editar la asociación con
  // proveedor (la Pydantic schema `MermaUpdateRequest` ya lo aceptaba; antes
  // la UI no lo enviaba, gap UI vs backend cerrado).
  const { proveedores } = useProveedores({ page_size: 100 });
  const [motivo, setMotivo] = useState<MotivoMerma>(inicial.motivo as MotivoMerma);
  const [observacion, setObservacion] = useState(inicial.observacion ?? "");
  const [productoId, setProductoId] = useState<number | null>(inicial.producto_id);
  const [cantidad, setCantidad] = useState<number>(inicial.cantidad);
  const [proveedorId, setProveedorId] = useState<number | null>(
    inicial.proveedor_id ?? null,
  );

  useEffect(() => {
    setMotivo(inicial.motivo as MotivoMerma);
    setObservacion(inicial.observacion ?? "");
    setProductoId(inicial.producto_id);
    setCantidad(inicial.cantidad);
    setProveedorId(inicial.proveedor_id ?? null);
  }, [inicial]);

  async function manejarSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!productoId) return;
    if (cantidad <= 0) return;
    const body: MermaUpdateBody = {
      motivo,
      observacion: observacion.trim() === "" ? null : observacion.trim(),
      producto_id: productoId,
      cantidad,
      // sdd/modulo-b-aprobaciones-detalle-editar (verify fix #6): enviar siempre
      // `proveedor_id` (incluso null) para que el backend lo persista; si no
      // lo incluimos, la Pydantic schema con extra="forbid" lo interpretaría
      // como null y la entidad trataría el campo como "no tocar".
      proveedor_id: proveedorId,
    };
    await onSubmit(body);
  }

  return (
    <form onSubmit={manejarSubmit} className="space-y-4">
      <SelectorProducto
        label="Producto"
        value={productoId}
        onChange={(id) => setProductoId(id)}
        requerido
      />
      <Input
        label="Cantidad"
        type="number"
        min={1}
        value={cantidad}
        onChange={(e) => setCantidad(Math.max(1, Number(e.target.value) || 1))}
        requerido
      />
      <Select
        label="Motivo"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value as MotivoMerma)}
        requerido
      >
        <option value="vencimiento">Vencimiento</option>
        <option value="rotura">Rotura</option>
        <option value="otro">Otro</option>
      </Select>
      <Select
        label="Proveedor (opcional)"
        value={proveedorId ?? ""}
        onChange={(e) =>
          setProveedorId(e.target.value ? Number(e.target.value) : null)
        }
      >
        <option value="">Sin proveedor</option>
        {proveedores.map((p) => (
          <option key={p.id} value={p.id}>
            {p.razon_social}
          </option>
        ))}
      </Select>
      <label className="block">
        <span className="mb-1 block text-sm font-medium text-zinc-700">Observación</span>
        <textarea
          value={observacion}
          onChange={(e) => setObservacion(e.target.value)}
          maxLength={1000}
          rows={3}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-500"
        />
      </label>

      {error && <Alert tono="peligro">{error}</Alert>}

      <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
        <Button type="button" variante="secundario" onClick={onCancel} disabled={procesando}>
          Cancelar
        </Button>
        <Button type="submit" cargando={procesando} disabled={!productoId || cantidad <= 0}>
          Guardar cambios
        </Button>
      </div>
    </form>
  );
}
