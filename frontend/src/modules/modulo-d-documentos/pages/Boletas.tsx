// Página de consulta/descarga de boletas generadas.
import { useState } from "react";
import { Download, Receipt } from "lucide-react";
import {
  Alert,
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
import { useBoletas } from "../hooks/useBoletas";
import type { Boleta } from "../types";

export default function Boletas() {
  const { boletas, cargando, error, noDisponible, recargar } = useBoletas();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Boletas" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos (Módulo D)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Boleta>[] = [
    { titulo: "Número", render: (b) => <span className="font-mono text-xs text-zinc-700">{b.numero}</span> },
    { titulo: "Venta", soloEscritorio: true, render: (b) => `#${b.venta_id}` },
    {
      titulo: "Emitida",
      render: (b) => (
        <span className="whitespace-nowrap text-zinc-500">
          {b.emitida_en ? new Date(b.emitida_en).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Total",
      alinear: "derecha",
      render: (b) => <span className="font-medium tabular-nums">S/ {b.total.toFixed(2)}</span>,
    },
    {
      titulo: "PDF",
      render: (b) =>
        b.url_pdf ? (
          <a href={b.url_pdf} target="_blank" rel="noreferrer">
            <Button variante="secundario" compacto icono={<Download className="h-4 w-4" aria-hidden />}>
              Descargar
            </Button>
          </a>
        ) : (
          <span className="text-xs text-zinc-400">No disponible</span>
        ),
    },
  ];

  return (
    <div>
      <PageHeader titulo="Boletas" descripcion="Comprobantes emitidos por cada venta." />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-44">
            <Input label="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          </div>
          <div className="w-44">
            <Input label="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          </div>
          <Button variante="secundario" onClick={() => void recargar(desde || undefined, hasta || undefined)}>
            Filtrar
          </Button>
        </div>
      </Card>

      {cargando && <PageSpinner texto="Cargando boletas…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={boletas}
            claveDe={(b) => b.id}
            vacio={
              <EmptyState
                icono={Receipt}
                titulo="Sin boletas"
                descripcion="No hay comprobantes en el período elegido."
              />
            }
          />
        </Card>
      )}
    </div>
  );
}
