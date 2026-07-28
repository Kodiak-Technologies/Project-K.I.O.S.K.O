// Página de generación/consulta de reportes de ventas (solo ADMIN).
import { useState } from "react";
import { ArrowDown, ArrowUp, BarChart3, Download } from "lucide-react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import {
  Alert,
  Button,
  Card,
  DatePicker,
  EmptyState,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { useReportes } from "../hooks/useReportes";
import type { TopProducto } from "../types";
import { GraficoVentasEgresos } from "../components/GraficoVentasEgresos";

const COLORES = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

function recortarNombre(nombre: string, maxPalabras: number = 3, maxChars: number = 22): string {
  if (!nombre) return "";
  const palabras = nombre.trim().split(/\s+/);
  let texto = nombre;
  if (palabras.length > maxPalabras) {
    texto = palabras.slice(0, maxPalabras).join(" ") + "...";
  } else if (texto.length > maxChars) {
    texto = texto.slice(0, maxChars - 3) + "...";
  }
  return texto;
}

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
  // Fecha en la zona LOCAL del usuario. `toISOString()` convierte a UTC, así que
  // de noche (p. ej. 23:40 en Perú, UTC−5) devolvía el día siguiente en "Hoy".
  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
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
    {
      titulo: "Producto",
      ancho: "50%",
      render: (p) => <span className="font-medium text-zinc-800 break-words">{p.nombre}</span>,
    },
    {
      titulo: "Unidades",
      ancho: "25%",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums font-semibold text-zinc-900">{p.cantidad}</span>,
    },
    {
      titulo: "Total",
      ancho: "25%",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums font-semibold text-zinc-900">S/ {p.total.toFixed(2)}</span>,
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

  const datosTopProductos = (resumen && orden === "mayor"
    ? resumen.top_productos
    : masVendidos
  ).map((p) => ({
    nombreCompleto: p.nombre,
    name: recortarNombre(p.nombre, 3, 22),
    cantidad: p.cantidad,
    total: p.total,
  }));

  return (
    <div>
      <PageHeader titulo="Reportes" descripcion="Resumen de ventas por período." />

      <Card className="mb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="grid flex-1 grid-cols-2 gap-3 sm:flex sm:flex-initial sm:items-end">
            <div className="w-full sm:w-44">
              <DatePicker label="Desde" requerido mostrarAnio value={desde} onChange={(val) => setDesde(val)} />
            </div>
            <div className="w-full sm:w-44">
              <DatePicker label="Hasta" requerido mostrarAnio value={hasta} onChange={(val) => setHasta(val)} />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              className="w-full sm:w-auto"
              disabled={!desde || !hasta}
              onClick={() => void generarReportes()}
              icono={<BarChart3 className="h-4 w-4" aria-hidden />}
            >
              Generar reporte
            </Button>
            {resumen && (
              <>
                <Button
                  variante="secundario"
                  className="flex-1 sm:flex-initial"
                  onClick={() => void exportar(desde, hasta, "resumen")}
                  icono={<Download className="h-4 w-4" aria-hidden />}
                >
                  Excel resumen
                </Button>
                <Button
                  variante="secundario"
                  className="flex-1 sm:flex-initial"
                  onClick={() => void exportar(desde, hasta, "egresos")}
                  icono={<ArrowDown className="h-4 w-4" aria-hidden />}
                >
                  Excel egresos
                </Button>
              </>
            )}
          </div>
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
            <Indicador
              etiqueta="Devoluciones"
              valor={`S/ ${(resumen.total_devuelto ?? 0).toFixed(2)}`}
            />
          </div>

          {/* Componente Moderno y Creativo para Ventas vs Egresos */}
          {resumen.total_vendido > 0 && (
            <GraficoVentasEgresos
              totalVendido={resumen.total_vendido}
              totalEgresos={resumen.total_egresos}
              totalDevuelto={resumen.total_devuelto}
              numeroVentas={resumen.numero_ventas}
            />
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
                        outerRadius={75}
                        paddingAngle={3}
                        dataKey="value"
                        label={({ percent }) => `${((percent ?? 0) * 100).toFixed(0)}%`}
                      >
                        {datosMetodosPago.map((_, i) => (
                          <Cell key={i} fill={COLORES[i % COLORES.length]} stroke="none" />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => `S/ ${Number(v).toFixed(2)}`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex w-full flex-col gap-2.5 sm:w-1/2">
                  {datosMetodosPago.map((m, i) => (
                    <div key={m.name} className="flex items-center justify-between gap-3 rounded-lg border border-zinc-100 bg-zinc-50/60 px-3.5 py-2 text-sm">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: COLORES[i % COLORES.length] }} />
                        <span className="font-medium text-zinc-700 truncate">{m.name}</span>
                      </div>
                      <span className="shrink-0 font-semibold tabular-nums text-zinc-900 whitespace-nowrap">S/ {m.value.toFixed(2)}</span>
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
              <div className="flex flex-wrap items-center gap-1.5 justify-end">
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
                  title="Más vendidos"
                  aria-label="Más vendidos"
                  icono={<ArrowUp className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    setOrden("mayor");
                    void generarMasVendidos(desde, hasta, criterio, "mayor");
                  }}
                >
                  <span className="hidden sm:inline">Más vendidos</span>
                </Button>
                <Button
                  variante={orden === "menor" ? "primario" : "secundario"}
                  compacto
                  title="Menor rotación"
                  aria-label="Menor rotación"
                  icono={<ArrowDown className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    setOrden("menor");
                    void generarMasVendidos(desde, hasta, criterio, "menor");
                  }}
                >
                  <span className="hidden sm:inline">Menor rotación</span>
                </Button>
              </div>
            }
          >
            {datosTopProductos.length > 0 && (
              <div className="p-4">
                <ResponsiveContainer width="100%" height={Math.max(280, datosTopProductos.length * 45)}>
                  <BarChart data={datosTopProductos} layout="vertical" margin={{ left: 130, right: 30, top: 10, bottom: 10 }}>
                    <defs>
                      <linearGradient id="gradTopProd" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.85} />
                        <stop offset="100%" stopColor="#1d4ed8" stopOpacity={1} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={125}
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: "#475569", fontSize: 12, fontWeight: 500 }}
                    />
                    <Tooltip
                      formatter={(v) => (criterio === "unidades" ? `${v} uds` : `S/ ${Number(v).toFixed(2)}`)}
                      labelFormatter={(_, payload) => {
                        if (payload && payload[0]) {
                          return payload[0].payload.nombreCompleto;
                        }
                        return "";
                      }}
                    />
                    <Bar
                      dataKey={criterio === "unidades" ? "cantidad" : "total"}
                      fill="url(#gradTopProd)"
                      radius={[0, 8, 8, 0]}
                      barSize={22}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <Table
              minAncho="0"
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
