// Página de caja: muestra el turno actual; si está cerrada permite abrirla y
// si está abierta enlaza al cierre. Es la pantalla "/caja" del sidebar.
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Wallet } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useCaja } from "../hooks/useCaja";

export default function AperturaCaja() {
  const { turno, cargando, error, noDisponible, abrir } = useCaja();
  const [montoInicial, setMontoInicial] = useState("");
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  async function manejarAbrir(evento: FormEvent) {
    evento.preventDefault();
    const monto = Number(montoInicial);
    if (Number.isNaN(monto) || monto < 0) {
      setErrorAccion("Ingresa el efectivo inicial (0 o más).");
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      await abrir(monto);
      setMontoInicial("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Caja" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas (Módulo C)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Consultando la caja…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const abierta = turno?.estado === "ABIERTO";

  return (
    <div className="max-w-xl">
      <PageHeader
        titulo="Caja"
        descripcion="Abre un turno al empezar el día y ciérralo al terminar."
        acciones={<Badge tono={abierta ? "exito" : "neutro"}>{abierta ? "Abierta" : "Cerrada"}</Badge>}
      />

      {abierta && turno ? (
        <Card titulo="Turno en curso">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-zinc-500">Abierta por</dt>
              <dd className="font-medium text-zinc-800">{turno.abierto_por}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Desde</dt>
              <dd className="font-medium text-zinc-800">
                {new Date(turno.abierto_en).toLocaleString("es-PE")}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500">Efectivo inicial</dt>
              <dd className="font-medium tabular-nums text-zinc-800">
                S/ {turno.monto_inicial.toFixed(2)}
              </dd>
            </div>
          </dl>
          <div className="mt-4">
            <Link to="/caja/cierre">
              <Button variante="secundario">Ir al cierre de caja</Button>
            </Link>
          </div>
        </Card>
      ) : (
        <Card titulo="Abrir turno" descripcion="Cuenta el efectivo con el que empieza la caja.">
          <form onSubmit={(e) => void manejarAbrir(e)} className="space-y-4">
            <Input
              label="Efectivo inicial (S/)"
              requerido
              type="number"
              step="0.10"
              min={0}
              inputMode="decimal"
              placeholder="0.00"
              value={montoInicial}
              onChange={(e) => setMontoInicial(e.target.value)}
            />
            {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
            <Button type="submit" cargando={procesando} icono={<Wallet className="h-4 w-4" aria-hidden />}>
              Abrir caja
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
