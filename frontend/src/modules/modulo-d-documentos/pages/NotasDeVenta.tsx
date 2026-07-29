import { useEffect, useState } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { CloudUpload, Download, FileText, X } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  DatePicker,
  EmptyState,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  PaginacionControles,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { useNotasVenta } from "../hooks/useNotasVenta";
import { notasVentaHttpAdapter } from "../services/notasVenta.http-adapter";
import type { NotaVenta } from "../types";

export default function NotasDeVenta() {
  const { notas, paginados, cargando, error, noDisponible, recargar } = useNotasVenta();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [descargandoId, setDescargandoId] = useState<number | null>(null);
  const [subiendoId, setSubiendoId] = useState<number | null>(null);
  const [mensajeDrive, setMensajeDrive] = useState<
    { tono: "exito" | "peligro"; texto: string } | null
  >(null);
  const [descargandoBatch, setDescargandoBatch] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  /** Rango efectivamente aplicado (el que viaja al backend). */
  const [rango, setRango] = useState<{ desde?: string; hasta?: string }>({});

  useEffect(() => {
    void recargar({ ...rango, page, page_size: pageSize });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rango, page, pageSize]);

  const filtrar = () => {
    setPage(1);
    setRango({ desde: desde || undefined, hasta: hasta || undefined });
  };

  const limpiarFiltros = () => {
    setDesde("");
    setHasta("");
    setPage(1);
    setRango({});
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

  const subirADrive = async (nv: NotaVenta) => {
    setSubiendoId(nv.venta_id);
    setMensajeDrive(null);
    try {
      const r = await notasVentaHttpAdapter.subirADrive(nv.venta_id);
      setMensajeDrive({
        tono: "exito",
        texto: `${nv.identificacion} archivada en Drive (${r.carpeta}).`,
      });
    } catch (e) {
      setMensajeDrive({ tono: "peligro", texto: mensajeDeError(e) });
    } finally {
      setSubiendoId(null);
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

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Notas de Venta" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<NotaVenta>[] = [
    {
      titulo: "Identificación",
      ancho: "230px",
      render: (nv) => <span className="font-mono text-xs text-zinc-700">{nv.identificacion}</span>,
    },
    {
      titulo: "Fecha",
      ancho: "185px",
      render: (nv) => (
        <span className="whitespace-nowrap text-zinc-500">
          {nv.fecha ? (isNaN(Date.parse(nv.fecha)) ? nv.fecha : new Date(nv.fecha).toLocaleString("es-PE")) : "—"}
        </span>
      ),
    },
    {
      titulo: "Método pago",
      ancho: "140px",
      render: (nv) => <Badge tono="neutro">{nv.metodo_pago}</Badge>,
    },
    {
      titulo: "Total",
      ancho: "120px",
      alinear: "derecha",
      render: (nv) => <span className="font-medium tabular-nums text-zinc-900">S/ {nv.total.toFixed(2)}</span>,
    },
    {
      titulo: "Acciones",
      ancho: "180px",
      alinear: "centro",
      render: (nv) => (
        <div className="flex justify-center gap-2">
          <Button
            variante="secundario"
            compacto
            icono={<Download className="h-4 w-4" aria-hidden />}
            onClick={() => void descargarPng(nv)}
            disabled={descargandoId === nv.venta_id}
          >
            PNG
          </Button>
          <Button
            variante="secundario"
            compacto
            icono={<CloudUpload className="h-4 w-4" aria-hidden />}
            onClick={() => void subirADrive(nv)}
            cargando={subiendoId === nv.venta_id}
            disabled={subiendoId !== null}
          >
            Drive
          </Button>
        </div>
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
          </div>
        }
      />

      <Card className="mb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="grid flex-1 grid-cols-2 gap-3 sm:flex sm:flex-initial sm:items-end">
            <div className="w-full sm:w-44">
              <DatePicker label="Desde" mostrarAnio value={desde} onChange={(val) => setDesde(val)} />
            </div>
            <div className="w-full sm:w-44">
              <DatePicker label="Hasta" mostrarAnio value={hasta} onChange={(val) => setHasta(val)} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button className="flex-1 sm:flex-initial" variante="secundario" onClick={filtrar}>
              Filtrar
            </Button>
            <Button className="flex-1 sm:flex-initial" variante="secundario" onClick={limpiarFiltros} icono={<X className="h-4 w-4" aria-hidden />}>
              Limpiar
            </Button>
          </div>
        </div>
      </Card>

      {cargando && <PageSpinner texto="Cargando notas de venta…" />}
      {mensajeDrive && (
        <div className="mb-3">
          <Alert tono={mensajeDrive.tono}>{mensajeDrive.texto}</Alert>
        </div>
      )}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            minAncho="650px"
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
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={(n) => {
              setPageSize(n);
              setPage(1);
            }}
            etiqueta="notas de venta"
          />
        </Card>
      )}
    </div>
  );
}
