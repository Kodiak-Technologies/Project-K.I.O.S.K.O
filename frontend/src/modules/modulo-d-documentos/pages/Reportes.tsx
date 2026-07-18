// Página de generación/consulta de reportes de ventas (solo ADMIN).
import { useState } from "react";
import { ArrowDown, ArrowUp, BarChart3 } from "lucide-react";
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
import type { ResumenReporte, TopProducto } from "../types";

function Indicador({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <Card>
      <p className="text-sm text-zinc-500">{etiqueta}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900">{valor}</p>
    </Card>
  );
}

export default function Reportes() {
  const { resumen, masVendidos, cargando, error, noDisponible, generar, generarMasVendidos } = useReportes();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [orden, setOrden] = useState<"mayor" | "menor">("mayor");

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

  const columnasTop: Columna<TopProducto>[] = [
    { titulo: "Producto", render: (p) => <span className="font-medium text-zinc-800">{p.nombre}</span> },
    { titulo: "Unidades", alinear: "derecha", render: (p) => <span className="tabular-nums">{p.cantidad}</span> },
    {
      titulo: "Total",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums">S/ {p.total.toFixed(2)}</span>,
    },
  ];

  const generarReportes = async () => {
    await generar(desde, hasta);
    await generarMasVendidos(desde, hasta, "unidades", orden);
  };

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
            onClick={() => void generarReportes()}
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
          <div className="grid gap-4 sm:grid-cols-4">
            <Indicador etiqueta="Total vendido" valor={`S/ ${resumen.total_vendido.toFixed(2)}`} />
            <Indicador etiqueta="Total egresos" valor={`S/ ${resumen.total_egresos.toFixed(2)}`} />
            <Indicador etiqueta="Ventas" valor={String(resumen.numero_ventas)} />
            <Indicador etiqueta="Ticket promedio" valor={`S/ ${resumen.ticket_promedio.toFixed(2)}`} />
          </div>

          {Object.keys(resumen.metodos_pago).length > 0 && (
            <Card titulo="Desglose por método de pago" sinPadding>
              <div className="grid gap-4 p-4 sm:grid-cols-2 md:grid-cols-4">
                {Object.entries(resumen.metodos_pago).map(([metodo, monto]) => (
                  <div key={metodo} className="rounded-lg border border-zinc-200 p-3">
                    <p className="text-sm text-zinc-500">{metodo}</p>
                    <p className="mt-1 text-lg font-semibold tabular-nums text-zinc-900">
                      S/ {(monto as number).toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card
            titulo={orden === "mayor" ? "Productos más vendidos" : "Productos de menor rotación"}
            sinPadding
            accion={
              <div className="flex gap-2">
                <Button
                  variante={orden === "mayor" ? "primario" : "secundario"}
                  compacto
                  icono={<ArrowUp className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    setOrden("mayor");
                    void generarMasVendidos(desde, hasta, "unidades", "mayor");
                  }}
                >
                  Más vendidos
                </Button>
                <Button
                  variante={orden === "menor" ? "primario" : "secundario"}
                  compacto
                  icono={<ArrowDown className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    setOrden("menor");
                    void generarMasVendidos(desde, hasta, "unidades", "menor");
                  }}
                >
                  Menor rotación
                </Button>
              </div>
            }
          >
            <Table
              columnas={columnasTop}
              filas={orden === "mayor" ? resumen.top_productos : masVendidos}
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
