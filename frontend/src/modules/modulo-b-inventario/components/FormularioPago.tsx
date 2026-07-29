// Formulario para registrar una compra a crédito o un pago a proveedor.
// Reutilizado en ProveedorDetalle.
import { useState } from "react";
import { Button, DatePicker, Input } from "../../../shared/components/ui";
import type { NuevoPagoProveedor } from "../types";

interface Props {
  /** Título que ve el usuario (ej. "Registrar compra a crédito"). */
  titulo: string;
  /** Deuda actual del proveedor (para limitar el pago). */
  deudaActual: number;
  /** Tipo de operación: para "PAGO" limitamos el monto a la deuda. */
  tipo: "COMPRA_CREDITO" | "PAGO";
  onSubmit: (datos: NuevoPagoProveedor) => Promise<void>;
  procesando: boolean;
  onCancelar: () => void;
}

// Fecha LOCAL de hoy. `toISOString()` da UTC, que de noche (Perú UTC−5) adelanta
// el valor por defecto al día siguiente.
const HOY = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export function FormularioPago({ titulo, deudaActual, tipo, onSubmit, procesando, onCancelar }: Props) {
  const [monto, setMonto] = useState<number>(0);
  const [fecha, setFecha] = useState<string>(HOY());
  const [concepto, setConcepto] = useState("");
  const [errores, setErrores] = useState<Record<string, string>>({});

  function validar(): boolean {
    const e: Record<string, string> = {};
    if (!(monto > 0)) e.monto = "El monto debe ser mayor a 0.";
    if (tipo === "PAGO" && monto > deudaActual) {
      e.monto = `El pago no puede superar la deuda actual (S/ ${deudaActual.toFixed(2)}).`;
    }
    if (!fecha) e.fecha = "Fecha obligatoria.";
    setErrores(e);
    return Object.keys(e).length === 0;
  }

  async function manejarSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validar()) return;
    await onSubmit({
      monto,
      fecha,
      concepto: concepto.trim() || null,
      solicitud_ingreso_id: null,
    });
  }

  return (
    <form onSubmit={(e) => void manejarSubmit(e)} className="space-y-3">
      <p className="text-sm text-zinc-600">{titulo}</p>
      <Input
        label="Monto (S/)"
        type="number"
        step="0.01"
        min={0.01}
        requerido
        value={monto || ""}
        onChange={(e) => setMonto(Number(e.target.value))}
        error={errores.monto}
      />
      <DatePicker
        label="Fecha"
        requerido
        valor={fecha}
        alCambiar={(val) => setFecha(val)}
        error={errores.fecha}
      />
      <Input
        label="Concepto (opcional)"
        placeholder={tipo === "COMPRA_CREDITO" ? "ej. Lote 24 Coca-Cola (Boleta 001)" : "ej. Pago parcial en efectivo"}
        value={concepto}
        onChange={(e) => setConcepto(e.target.value)}
      />
      <div className="flex justify-end gap-2 pt-1">
        <Button
          type="button"
          variante="secundario"
          onClick={onCancelar}
          disabled={procesando}
        >
          Cancelar
        </Button>
        <Button
          type="submit"
          cargando={procesando}
        >
          Registrar
        </Button>
      </div>
    </form>
  );
}
