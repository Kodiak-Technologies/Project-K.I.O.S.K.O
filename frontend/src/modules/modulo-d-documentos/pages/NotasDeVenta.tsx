// Página de consulta/descarga de notas de venta.
import { useState } from "react";
import { Download, FileText, Upload, X } from "lucide-react";
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
import { useNotasVenta } from "../hooks/useNotasVenta";
import { notasVentaHttpAdapter } from "../services/notasVenta.http-adapter";
import type { NotaVenta } from "../types";

export default function NotasDeVenta() {
  const { notas, cargando, error, noDisponible, recargar } = useNotasVenta();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [descargandoId, setDescargandoId] = useState<number | null>(null);
  const [descargandoBatch, setDescargandoBatch] = useState(false);
  const [subiendoBatch, setSubiendoBatch] = useState(false);

  const filtrar = () => void recargar(desde || undefined, hasta || undefined);

  const limpiarFiltros = () => {
    setDesde("");
    setHasta("");
    void recargar();
  };

  const teclaEnter = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") filtrar();
  };

  const descargarPng = async (nv: NotaVenta) => {
    setDescargandoId(nv.venta_id);
    try {
      const blob = await notasVentaHttpAdapter.descargarPng(nv.venta_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${nv.identificacion}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
    } finally {
      setDescargandoId(null);
    }
  };

  const descargarBatch = async () => {
    setDescargandoBatch(true);
    try {
      const blob = await notasVentaHttpAdapter.descargarBatch(
        desde || undefined,
        hasta || undefined
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "notas-venta.zip";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
    } finally {
      setDescargandoBatch(false);
    }
  };

  const subirDriveBatch = async () => {
    setSubiendoBatch(true);
    try {
      await notasVentaHttpAdapter.subirDriveBatch(desde || undefined, hasta || undefined);
      void recargar(desde || undefined, hasta || undefined);
    } catch {
    } finally {
      setSubiendoBatch(false);
    }
  };

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Notas de Venta" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos (Módulo D)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<NotaVenta>[] = [
    {
      titulo: "Identificación",
      render: (nv) => <span className="font-mono text-xs text-zinc-700">{nv.identificacion}</span>,
    },
    {
      titulo: "Fecha",
      render: (nv) => <span className="whitespace-nowrap text-zinc-500">{nv.fecha}</span>,
    },
    {
      titulo: "Método pago",
      render: (nv) => <span className="text-zinc-600">{nv.metodo_pago}</span>,
    },
    {
      titulo: "Total",
      alinear: "derecha",
      render: (nv) => <span className="font-medium tabular-nums">S/ {nv.total.toFixed(2)}</span>,
    },
    {
      titulo: "Acciones",
      render: (nv) => (
        <Button
          variante="secundario"
          compacto
          icono={<Download className="h-4 w-4" aria-hidden />}
          onClick={() => void descargarPng(nv)}
          disabled={descargandoId === nv.venta_id}
        >
          PNG
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Notas de Venta"
        descripcion="Notas de venta generadas a partir de las ventas registradas."
        acciones={
          <div className="flex gap-2">
            <Button
              variante="secundario"
              icono={<Download className="h-4 w-4" aria-hidden />}
              onClick={() => void descargarBatch()}
              disabled={descargandoBatch}
            >
              {descargandoBatch ? "Descargando…" : "Descargar ZIP"}
            </Button>
            <Button
              variante="primario"
              icono={<Upload className="h-4 w-4" aria-hidden />}
              onClick={() => void subirDriveBatch()}
              disabled={subiendoBatch}
            >
              {subiendoBatch ? "Subiendo…" : "Subir a Drive"}
            </Button>
          </div>
        }
      />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-44">
            <Input label="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} onKeyDown={teclaEnter} />
          </div>
          <div className="w-44">
            <Input label="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} onKeyDown={teclaEnter} />
          </div>
          <Button variante="secundario" onClick={filtrar}>
            Filtrar
          </Button>
          <Button variante="secundario" onClick={limpiarFiltros} icono={<X className="h-4 w-4" aria-hidden />}>
            Limpiar
          </Button>
        </div>
      </Card>

      {cargando && <PageSpinner texto="Cargando notas de venta…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={notas}
            claveDe={(nv) => nv.venta_id}
            vacio={
              <EmptyState
                icono={FileText}
                titulo="Sin notas de venta"
                descripcion="No hay notas de venta en el período elegido."
              />
            }
          />
        </Card>
      )}
    </div>
  );
}
