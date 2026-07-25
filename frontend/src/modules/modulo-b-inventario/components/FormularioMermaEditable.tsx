// sdd/modulo-b-aprobaciones-detalle-editar: editable form for Merma.
// Single-product, motivo select, observacion textarea. No lineas.
import { useEffect, useState } from "react";
import { Alert, Button, Input, Select } from "../../../shared/components/ui";
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
  const [motivo, setMotivo] = useState<MotivoMerma>(inicial.motivo as MotivoMerma);
  const [observacion, setObservacion] = useState(inicial.observacion ?? "");
  const [productoId, setProductoId] = useState<number | null>(inicial.producto_id);
  const [cantidad, setCantidad] = useState<number>(inicial.cantidad);

  useEffect(() => {
    setMotivo(inicial.motivo as MotivoMerma);
    setObservacion(inicial.observacion ?? "");
    setProductoId(inicial.producto_id);
    setCantidad(inicial.cantidad);
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
