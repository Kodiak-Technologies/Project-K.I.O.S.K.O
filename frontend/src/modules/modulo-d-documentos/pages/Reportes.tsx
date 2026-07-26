// Página de generación/consulta de reportes de ventas (solo ADMIN).
import { useState } from "react";
import { ArrowDown, ArrowUp, BarChart3, Download } from "lucide-react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
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

const COLORES = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

function Indicador({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <Card>
      <p className="text-sm text-zinc-500">{etiqueta}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900">{valor}</p>
    </Card>
  );
}

function presets() {
  const hoy = new Date();
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  const inicioSemana = new Date(hoy);
  inicioSemana.setDate(hoy.getDate() - hoy.getDay());
  const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const inicioAnio = new Date(hoy.getFullYear(), 0, 1);
  return [
    { label: "Hoy", desde: fmt(hoy), hasta: fmt(hoy) },
    { label: "Semana", desde: fmt(inicioSemana), hasta: fmt(hoy) },
    { label: "Mes", desde: fmt(inicioMes), hasta: fmt(hoy) },
    { label: "Año", desde: fmt(inicioAnio), hasta: fmt(hoy) },
  ];
}

export default function Reportes() {
  const { resumen, masVendidos, cargando, error, noDisponible, generar, generarMasVendidos, exportar } = useReportes();
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [criterio, setCriterio] = useState<"unidades" | "monto">("unidades");
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
    await generarMasVendidos(desde, hasta, criterio, orden);
  };

  const aplicarPreset = async (p: { desde: string; hasta: string }) => {
    setDesde(p.desde);
    setHasta(p.hasta);
    await generar(p.desde, p.hasta);
    await generarMasVendidos(p.desde, p.hasta, criterio, orden);
  };

  const toggleCriterio = async (nuevo: "unidades" | "monto") => {
    setCriterio(nuevo);
    if (desde && hasta) {
      await generarMasVendidos(desde, hasta, nuevo, orden);
    }
  };

  const datosMetodosPago = resumen
    ? Object.entries(resumen.metodos_pago).map(([metodo, monto]) => ({ name: metodo, value: monto }))
    : [];

  const datosTopProductos = resumen && orden === "mayor"
    ? resumen.top_productos.map((p) => ({ name: p.nombre, cantidad: p.cantidad, total: p.total }))
    : masVendidos.map((p) => ({ name: p.nombre, cantidad: p.cantidad, total: p.total }));

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
          {resumen && (
            <Button
              variante="secundario"
              onClick={() => void exportar(desde, hasta, "resumen")}
              icono={<Download className="h-4 w-4" aria-hidden />}
            >
              Excel
            </Button>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {presets().map((p) => (
            <Button
              key={p.label}
              variante="secundario"
              compacto
              onClick={() => void aplicarPreset(p)}
            >
              {p.label}
            </Button>
          ))}
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
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Indicador etiqueta="Total vendido" valor={`S/ ${resumen.total_vendido.toFixed(2)}`} />
            <Indicador etiqueta="Total egresos" valor={`S/ ${resumen.total_egresos.toFixed(2)}`} />
            <Indicador etiqueta="Ventas" valor={String(resumen.numero_ventas)} />
            <Indicador etiqueta="Ticket promedio" valor={`S/ ${resumen.ticket_promedio.toFixed(2)}`} />
            {/* Explica por qué lo cobrado por método puede superar lo vendido. */}
            <Indicador
              etiqueta="Devoluciones"
              valor={`S/ ${(resumen.total_devuelto ?? 0).toFixed(2)}`}
            />
          </div>

          {resumen.total_vendido > 0 && (
            <Card titulo="Ventas vs Egresos" sinPadding>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={[{ name: "Período", ventas: resumen.total_vendido, egresos: resumen.total_egresos }]}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(v) => `S/ ${Number(v).toFixed(2)}`} />
                    <Legend />
                    <Bar dataKey="ventas" fill="#3b82f6" name="Ventas" />
                    <Bar dataKey="egresos" fill="#ef4444" name="Egresos" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {datosMetodosPago.length > 0 && (
            <Card titulo="Cobrado por método de pago" sinPadding>
              <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
                <div className="w-full sm:w-1/2">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={datosMetodosPago}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                      >
                        {datosMetodosPago.map((_, i) => (
                          <Cell key={i} fill={COLORES[i % COLORES.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => `S/ ${Number(v).toFixed(2)}`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-1">
                  {datosMetodosPago.map((m, i) => (
                    <div key={m.name} className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORES[i % COLORES.length] }} />
                      <span className="text-sm text-zinc-600">{m.name}</span>
                      <span className="ml-auto font-semibold tabular-nums text-zinc-900">S/ {m.value.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}

          <Card
            titulo={orden === "mayor" ? "Productos más vendidos" : "Productos de menor rotación"}
            sinPadding
            accion={
              <div className="flex gap-2">
                <Button
                  variante={criterio === "unidades" ? "primario" : "secundario"}
                  compacto
                  onClick={() => void toggleCriterio("unidades")}
                >
                  Unidades
                </Button>
                <Button
                  variante={criterio === "monto" ? "primario" : "secundario"}
                  compacto
                  onClick={() => void toggleCriterio("monto")}
                >
                  Monto
                </Button>
                <Button
                  variante={orden === "mayor" ? "primario" : "secundario"}
                  compacto
                  icono={<ArrowUp className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    setOrden("mayor");
                    void generarMasVendidos(desde, hasta, criterio, "mayor");
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
                    void generarMasVendidos(desde, hasta, criterio, "menor");
                  }}
                >
                  Menor rotación
                </Button>
              </div>
            }
          >
            {datosTopProductos.length > 0 && (
              <div className="p-4">
                <ResponsiveContainer width="100%" height={Math.max(250, datosTopProductos.length * 35)}>
                  <BarChart data={datosTopProductos} layout="vertical" margin={{ left: 80 }}>
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" width={80} />
                    <Tooltip formatter={(v) => criterio === "unidades" ? `${v} uds` : `S/ ${Number(v).toFixed(2)}`} />
                    <Bar dataKey={criterio === "unidades" ? "cantidad" : "total"} fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
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
