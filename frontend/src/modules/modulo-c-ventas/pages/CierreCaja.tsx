// Página de cierre de caja al final de un turno: se cuenta el efectivo real
// y el backend calcula la diferencia contra lo esperado.
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Lock } from "lucide-react";
import {
  Alert,
  Button,
  Card,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useCaja } from "../hooks/useCaja";

export default function CierreCaja() {
  const { turno, cargando, error, noDisponible, cerrar } = useCaja();
  const navegar = useNavigate();
  const [montoFinal, setMontoFinal] = useState("");
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  async function manejarCerrar(evento: FormEvent) {
    evento.preventDefault();
    const monto = Number(montoFinal);
    if (Number.isNaN(monto) || monto < 0) {
      setErrorAccion("Ingresa el efectivo contado (0 o más).");
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      await cerrar(monto);
      navegar("/caja");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Cierre de caja" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas (Módulo C)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Consultando la caja…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  if (turno?.estado !== "ABIERTO") {
    return (
      <div className="max-w-xl">
        <PageHeader titulo="Cierre de caja" />
        <Alert tono="info">No hay un turno abierto. Abre la caja primero.</Alert>
      </div>
    );
  }

  return (
    <div className="max-w-xl">
      <PageHeader
        titulo="Cierre de caja"
        descripcion={`Turno abierto por ${turno.abierto_por} el ${new Date(turno.abierto_en).toLocaleString("es-PE")}.`}
      />

      <Card titulo="Cerrar turno" descripcion="Cuenta todo el efectivo de la caja antes de cerrar.">
        <form onSubmit={(e) => void manejarCerrar(e)} className="space-y-4">
          <Input
            label="Efectivo contado (S/)"
            requerido
            type="number"
            step="0.10"
            min={0}
            inputMode="decimal"
            placeholder="0.00"
            value={montoFinal}
            onChange={(e) => setMontoFinal(e.target.value)}
          />
          <p className="text-xs text-zinc-500">
            El sistema comparará este monto con lo esperado (inicial + ventas en efectivo) y
            registrará la diferencia en la bitácora.
          </p>
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
          <Button type="submit" variante="peligro" cargando={procesando} icono={<Lock className="h-4 w-4" aria-hidden />}>
            Cerrar caja
          </Button>
        </form>
      </Card>
    </div>
  );
}
