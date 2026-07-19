// Página de consulta/descarga de boletas generadas.
import { useState } from "react";
import { Download, Receipt, Upload, X } from "lucide-react";
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
import { useBoletas } from "../hooks/useBoletas";
import { boletasHttpAdapter } from "../services/boletas.http-adapter";
import type { Boleta } from "../types";

export default function Boletas() {
  const { boletas, cargando, error, noDisponible, recargar } = useBoletas();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [cliente, setCliente] = useState("");
  const [descargandoId, setDescargandoId] = useState<number | null>(null);
  const [subiendoId, setSubiendoId] = useState<number | null>(null);

  const filtrar = () => void recargar(desde || undefined, hasta || undefined, cliente || undefined);

  const limpiarFiltros = () => {
    setDesde("");
    setHasta("");
    setCliente("");
    void recargar();
  };

  const teclaEnter = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") filtrar();
  };

  const descargarPng = async (b: Boleta) => {
    setDescargandoId(b.id);
    try {
      const blob = await boletasHttpAdapter.descargarPng(b.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BOL-${b.numero}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
    } finally {
      setDescargandoId(null);
    }
  };

  const subirDrive = async (b: Boleta) => {
    setSubiendoId(b.id);
    try {
      await boletasHttpAdapter.subirDrive(b.id);
      void recargar(desde || undefined, hasta || undefined, cliente || undefined);
    } catch {
    } finally {
      setSubiendoId(null);
    }
  };

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
      titulo: "Cliente",
      render: (b) => <span className="text-zinc-600">{b.cliente_nombre ?? "—"}</span>,
    },
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
      titulo: "Boleta",
      render: (b) => (
        <div className="flex gap-1">
          <Button
            variante="secundario"
            compacto
            icono={<Download className="h-4 w-4" aria-hidden />}
            onClick={() => void descargarPng(b)}
            disabled={descargandoId === b.id}
          >
            {descargandoId === b.id ? "Descargando…" : "PNG"}
          </Button>
          <Button
            variante="secundario"
            compacto
            icono={<Upload className="h-4 w-4" aria-hidden />}
            onClick={() => void subirDrive(b)}
            disabled={subiendoId === b.id}
          >
            {subiendoId === b.id ? "Subiendo…" : "Drive"}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader titulo="Boletas" descripcion="Comprobantes emitidos por cada venta." />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-44">
            <Input label="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} onKeyDown={teclaEnter} />
          </div>
          <div className="w-44">
            <Input label="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} onKeyDown={teclaEnter} />
          </div>
          <div className="w-44">
            <Input label="Cliente" value={cliente} onChange={(e) => setCliente(e.target.value)} onKeyDown={teclaEnter} placeholder="Buscar por cliente" />
          </div>
          <Button variante="secundario" onClick={filtrar}>
            Filtrar
          </Button>
          <Button variante="secundario" onClick={limpiarFiltros} icono={<X className="h-4 w-4" aria-hidden />}>
            Limpiar
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
