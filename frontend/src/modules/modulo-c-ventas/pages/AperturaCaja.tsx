// Página de caja ("/caja"): muestra el turno actual, permite abrirlo si está
// cerrada y enlaza al cierre. A la derecha, el historial de aperturas y cierres,
// visible para TODOS los usuarios: en un cambio de turno el cajero entrante ve
// con cuánto abrió y cerró el anterior; la administradora supervisa lo mismo.
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { History, Wallet } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useCaja } from "../hooks/useCaja";
import type { TurnoCaja } from "../types";

function fechaCorta(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" }) : "—";
}

export default function AperturaCaja() {
  const { turno, turnos, cargando, error, noDisponible, abrir } = useCaja();
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

  const columnas: Columna<TurnoCaja>[] = [
    { titulo: "N°", render: (t) => <span className="font-mono text-xs text-zinc-500">#{t.id}</span> },
    { titulo: "Abierta por", render: (t) => <span className="font-medium text-zinc-800">{t.abierto_por}</span> },
    {
      titulo: "Apertura",
      render: (t) => <span className="whitespace-nowrap text-zinc-500">{fechaCorta(t.abierto_en)}</span>,
    },
    {
      titulo: "Monto inicial",
      alinear: "derecha",
      render: (t) => <span className="tabular-nums">S/ {t.monto_inicial.toFixed(2)}</span>,
    },
    {
      titulo: "Cierre",
      soloEscritorio: true,
      render: (t) => <span className="whitespace-nowrap text-zinc-500">{fechaCorta(t.cerrado_en)}</span>,
    },
    {
      titulo: "Contado al cierre",
      alinear: "derecha",
      render: (t) => (
        <span className="tabular-nums">{t.monto_final !== null ? `S/ ${t.monto_final.toFixed(2)}` : "—"}</span>
      ),
    },
    { titulo: "Cerrada por", soloEscritorio: true, render: (t) => t.cerrado_por ?? "—" },
    {
      titulo: "Estado",
      render: (t) =>
        t.estado === "ABIERTO" ? <Badge tono="exito">Abierto</Badge> : <Badge tono="neutro">Cerrado</Badge>,
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Caja"
        descripcion="Abre un turno al empezar el día y ciérralo al terminar. Todos ven las aperturas y cierres."
        acciones={<Badge tono={abierta ? "exito" : "neutro"}>{abierta ? "Abierta" : "Cerrada"}</Badge>}
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(20rem,24rem)_1fr]">
        {/* Columna izquierda: turno en curso o formulario de apertura */}
        <div className="space-y-4">
          {abierta && turno ? (
            <Card titulo="Turno en curso">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-zinc-500">Abierta por</dt>
                  <dd className="font-medium text-zinc-800">{turno.abierto_por}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Desde</dt>
                  <dd className="font-medium text-zinc-800">{fechaCorta(turno.abierto_en)}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Efectivo inicial</dt>
                  <dd className="font-medium tabular-nums text-zinc-800">
                    S/ {turno.monto_inicial.toFixed(2)}
                  </dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/pos">
                  <Button>Ir a vender</Button>
                </Link>
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
                <p className="text-xs text-zinc-500">
                  Tu apertura queda registrada con tu nombre, fecha y hora, y es visible para
                  el resto del equipo. No se puede vender sin un turno abierto.
                </p>
                {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
                <Button type="submit" cargando={procesando} icono={<Wallet className="h-4 w-4" aria-hidden />}>
                  Abrir caja
                </Button>
              </form>
            </Card>
          )}
        </div>

        {/* Columna derecha: historial de turnos (aprovecha el resto de la pantalla) */}
        <Card titulo="Historial de turnos" sinPadding>
          <Table
            columnas={columnas}
            filas={turnos}
            claveDe={(t) => t.id}
            vacio={
              <EmptyState
                icono={History}
                titulo="Sin turnos registrados"
                descripcion="Cuando se abra la primera caja aparecerá aquí."
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
