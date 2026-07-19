// Formulario de Merma (paso 1: registrar).
// Reutilizado en Mermas y como paso 1 en AprobacionMermas (sólo admin que crea la cola).
import { useState } from "react";
import { Button, Card, Input, Select } from "../../../shared/components/ui";
import { useProveedores } from "../hooks/useProveedores";
import { useProductos } from "../hooks/useProductos";
import type { MotivoMerma, NuevaMerma } from "../types";
import { SelectorProducto } from "./SelectorProducto";

interface Props {
  /** Si el usuario actual puede elegir el motivo (cajero solo registra). */
  alRegistrar: (datos: NuevaMerma) => Promise<void>;
  procesando: boolean;
  /** Producto preseleccionado (caso "Reportar merma" desde catálogo). */
  productoInicialId?: number | null;
}

const MOTIVOS: { value: MotivoMerma; label: string }[] = [
  { value: "vencimiento", label: "Vencimiento" },
  { value: "rotura", label: "Rotura" },
  { value: "otro", label: "Otro" },
];

const FORMULARIO_VACIO: NuevaMerma = {
  producto_id: 0,
  cantidad: 1,
  motivo: "vencimiento",
  observacion: null,
  proveedor_id: null,
};

export function FormularioMerma({ alRegistrar, procesando, productoInicialId }: Props) {
  const { proveedores } = useProveedores({ page_size: 100 });
  const [formulario, setFormulario] = useState<NuevaMerma>({
    ...FORMULARIO_VACIO,
    producto_id: productoInicialId ?? 0,
  });
  const [error, setError] = useState<string | null>(null);

  async function manejarEnvio(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!formulario.producto_id) {
      setError("Elegí un producto.");
      return;
    }
    if (formulario.cantidad < 1) {
      setError("La cantidad debe ser mayor a 0.");
      return;
    }
    try {
      await alRegistrar({
        ...formulario,
        observacion: formulario.observacion?.trim() ? formulario.observacion.trim() : null,
      });
      setFormulario({ ...FORMULARIO_VACIO, producto_id: productoInicialId ?? 0 });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar la merma.");
    }
  }

  return (
    <Card titulo="Registrar merma" descripcion="Queda en estado Pendiente hasta que un ADMIN la confirme.">
      <form onSubmit={(e) => void manejarEnvio(e)} className="space-y-3">
        <SelectorProducto
          label="Producto"
          requerido
          value={formulario.producto_id || null}
          onChange={(id) => setFormulario({ ...formulario, producto_id: id ?? 0 })}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Cantidad"
            type="number"
            min={1}
            requerido
            value={formulario.cantidad}
            onChange={(e) => setFormulario({ ...formulario, cantidad: Number(e.target.value) })}
          />
          <Select
            label="Motivo"
            value={formulario.motivo}
            onChange={(e) =>
              setFormulario({ ...formulario, motivo: e.target.value as MotivoMerma })
            }
          >
            {MOTIVOS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </Select>
        </div>
        <Select
          label="Proveedor (opcional)"
          value={formulario.proveedor_id ?? ""}
          onChange={(e) =>
            setFormulario({
              ...formulario,
              proveedor_id: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">Sin proveedor</option>
          {proveedores.map((p) => (
            <option key={p.id} value={p.id}>
              {p.razon_social}
            </option>
          ))}
        </Select>
        <Input
          label="Observación (opcional)"
          placeholder="ej. Vencen el 2026-07-15"
          value={formulario.observacion ?? ""}
          onChange={(e) => setFormulario({ ...formulario, observacion: e.target.value })}
        />
        {error && <p className="text-xs text-red-700">{error}</p>}
        <div className="flex justify-end">
          <Button type="submit" cargando={procesando}>
            Registrar merma
          </Button>
        </div>
      </form>
    </Card>
  );
}
