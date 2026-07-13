// Página de generación/consulta de reportes de ventas (solo ADMIN).
import { useState } from "react";
import { BarChart3 } from "lucide-react";
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
import { useReportes } from "../hooks/useReportes";
import type { ResumenReporte } from "../types";

function Indicador({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <Card>
      <p className="text-sm text-zinc-500">{etiqueta}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900">{valor}</p>
    </Card>
  );
}

export default function Reportes() {
  const { resumen, cargando, error, noDisponible, generar } = useReportes();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Reportes" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos (Módulo D)" />
        </Card>
      </div>
    );
  }

  const columnasTop: Columna<ResumenReporte["top_productos"][number]>[] = [
    { titulo: "Producto", render: (p) => <span className="font-medium text-zinc-800">{p.nombre}</span> },
    { titulo: "Unidades", alinear: "derecha", render: (p) => <span className="tabular-nums">{p.cantidad}</span> },
    {
      titulo: "Total",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums">S/ {p.total.toFixed(2)}</span>,
    },
  ];

  return (
    <div>
      <PageHeader titulo="Reportes" descripcion="Resumen de ventas por período." />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-44">
            <Input label="Desde" requerido type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          </div>
          <div className="w-44">
            <Input label="Hasta" requerido type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          </div>
          <Button
            disabled={!desde || !hasta}
            onClick={() => void generar(desde, hasta)}
            icono={<BarChart3 className="h-4 w-4" aria-hidden />}
          >
            Generar reporte
          </Button>
        </div>
      </Card>

      {cargando && <PageSpinner texto="Generando reporte…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!resumen && !cargando && !error && (
        <Card sinPadding>
          <EmptyState
            icono={BarChart3}
            titulo="Elige un período"
            descripcion="Selecciona las fechas y genera el reporte."
          />
        </Card>
      )}

      {resumen && !cargando && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <Indicador etiqueta="Total vendido" valor={`S/ ${resumen.total_vendido.toFixed(2)}`} />
            <Indicador etiqueta="Ventas" valor={String(resumen.numero_ventas)} />
            <Indicador etiqueta="Ticket promedio" valor={`S/ ${resumen.ticket_promedio.toFixed(2)}`} />
          </div>
          <Card titulo="Productos más vendidos" sinPadding>
            <Table
              columnas={columnasTop}
              filas={resumen.top_productos}
              claveDe={(p) => p.nombre}
              vacio={
                <EmptyState icono={BarChart3} titulo="Sin datos" descripcion="No hubo ventas en el período." />
              }
            />
          </Card>
        </div>
      )}
    </div>
  );
}
