// Página de generación/consulta de reportes de ventas (solo ADMIN).
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, BarChart3, Download, PieChart } from "lucide-react";
import { PieChart as RechartsPieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
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
import type { CostoProveedor, TopProducto } from "../types";
import { GraficoVentasEgresos } from "../components/GraficoVentasEgresos";

const COLORES_FALLBACK = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

/** Colores por método de pago — consistentes con los minicards del modal de caja. */
const COLORES_POR_METODO: Record<string, string> = {
  EFECTIVO: "#10b981",      // emerald-500
  YAPE: "#a855f7",          // purple-500
  PLIN: "#f59e0b",          // amber-500
  TRANSFERENCIA: "#3b82f6", // blue-500
  TARJETA: "#71717a",       // zinc-500 (gris)
};

function colorParaMetodo(metodo: string, indice: number): string {
  return COLORES_POR_METODO[metodo.toUpperCase()] ?? COLORES_FALLBACK[indice % COLORES_FALLBACK.length];
}

/** Etiqueta con la que el backend agrupa las solicitudes sin proveedor. */
const SIN_PROVEEDOR = "Sin proveedor";

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
  const [esMobile, setEsMobile] = useState(() => typeof window !== "undefined" && window.innerWidth < 640);

  useEffect(() => {
    const manejarResize = () => {
      setEsMobile(window.innerWidth < 640);
    };
    window.addEventListener("resize", manejarResize);
    return () => window.removeEventListener("resize", manejarResize);
  }, []);

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

  // Costo de mercadería por proveedor. Sale de las solicitudes de ingreso
  // aprobadas, así que suma igual que `total_egresos`. Las solicitudes sin
  // proveedor llegan del backend agrupadas como "Sin proveedor".
  const costoProveedores = resumen?.costo_por_proveedor ?? [];
  const totalCostoProveedores = costoProveedores.reduce((s, c) => s + c.monto, 0);
  const datosCostoProveedor = costoProveedores.map((c) => ({
    nombreCompleto: c.proveedor,
    name: recortarNombre(c.proveedor, 3, 22),
    monto: c.monto,
  }));

  const columnasCostoProveedor: Columna<CostoProveedor>[] = [
    { titulo: "Proveedor", render: (c) => c.proveedor },
    {
      titulo: "Ingresos",
      alinear: "derecha",
      soloEscritorio: true,
      render: (c) => <span className="tabular-nums">{c.ingresos}</span>,
    },
    {
      titulo: "Unidades",
      alinear: "derecha",
      soloEscritorio: true,
      render: (c) => <span className="tabular-nums">{c.unidades}</span>,
    },
    {
      titulo: "Costo",
      alinear: "derecha",
      render: (c) => (
        <span className="font-semibold tabular-nums">S/ {c.monto.toFixed(2)}</span>
      ),
    },
    {
      titulo: "% del total",
      alinear: "derecha",
      render: (c) => (
        <span className="tabular-nums text-zinc-500">
          {totalCostoProveedores > 0
            ? ((c.monto / totalCostoProveedores) * 100).toFixed(1)
            : "0.0"}
          %
        </span>
      ),
    },
  ];

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
            <div className="overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-sm transition-all duration-300 hover:shadow-md">
              {/* Header */}
              <div className="border-b border-zinc-100 bg-gradient-to-r from-zinc-50/80 via-white to-zinc-50/50 px-5 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600 shadow-inner">
                    <PieChart className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-zinc-900">Cobrado por Método de Pago</h3>
                    <p className="text-xs text-zinc-500 mt-0.5">Distribución de ingresos según medio de cobro</p>
                  </div>
                </div>
              </div>

              <div className="p-5">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
                  {/* Pie Chart */}
                  <div className="w-full sm:w-1/2">
                    <ResponsiveContainer width="100%" height={240}>
                      <RechartsPieChart>
                        <defs>
                          {datosMetodosPago.map((d, i) => (
                            <linearGradient key={d.name} id={`gradMetodo_${d.name}`} x1="0" y1="0" x2="1" y2="1">
                              <stop offset="0%" stopColor={colorParaMetodo(d.name, i)} stopOpacity={0.9} />
                              <stop offset="100%" stopColor={colorParaMetodo(d.name, i)} stopOpacity={0.65} />
                            </linearGradient>
                          ))}
                        </defs>
                        <Pie
                          data={datosMetodosPago}
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={85}
                          paddingAngle={4}
                          dataKey="value"
                          strokeWidth={2}
                          stroke="#fff"
                          label={({ percent }) => `${((percent ?? 0) * 100).toFixed(0)}%`}
                        >
                          {datosMetodosPago.map((d, i) => (
                            <Cell key={i} fill={`url(#gradMetodo_${d.name})`} />
                          ))}
                        </Pie>
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const item = payload[0];
                              const color = colorParaMetodo(item.name as string, 0);
                              return (
                                <div className="rounded-xl border border-zinc-200/80 bg-white/95 p-3 shadow-xl backdrop-blur-md">
                                  <div className="flex items-center gap-2">
                                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                                    <span className="text-xs font-semibold text-zinc-500">{item.name}</span>
                                  </div>
                                  <p className="mt-1 text-base font-extrabold text-zinc-900 tabular-nums">
                                    S/ {Number(item.value).toFixed(2)}
                                  </p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                      </RechartsPieChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Legend cards */}
                  <div className="flex w-full flex-col gap-2 sm:w-1/2">
                    {datosMetodosPago.map((m, i) => {
                      const color = colorParaMetodo(m.name, i);
                      const total = datosMetodosPago.reduce((s, d) => s + d.value, 0);
                      const pct = total > 0 ? ((m.value / total) * 100).toFixed(1) : "0.0";
                      return (
                        <div
                          key={m.name}
                          className="group relative overflow-hidden rounded-xl border border-zinc-100 bg-gradient-to-r from-zinc-50/60 via-white to-zinc-50/30 px-4 py-2.5 text-sm transition-all hover:-translate-y-0.5 hover:shadow-sm"
                        >
                          {/* accent bar */}
                          <div
                            className="absolute inset-y-0 left-0 w-1 rounded-l-xl"
                            style={{ backgroundColor: color }}
                          />
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <span
                                className="h-3 w-3 shrink-0 rounded-full shadow-sm"
                                style={{ backgroundColor: color }}
                              />
                              <span className="font-semibold text-zinc-700 truncate">{m.name}</span>
                              <span className="text-[11px] font-medium text-zinc-400">{pct}%</span>
                            </div>
                            <span className="shrink-0 font-bold tabular-nums text-zinc-900 whitespace-nowrap">
                              S/ {m.value.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Gasto en mercadería por proveedor */}
          <div className="overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-sm transition-all duration-300 hover:shadow-md">
            <div className="border-b border-zinc-100 bg-gradient-to-r from-zinc-50/80 via-white to-zinc-50/50 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600 shadow-inner">
                  <BarChart3 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-zinc-900">Costo por Proveedor</h3>
                  <p className="text-xs text-zinc-500 mt-0.5">Gasto en mercadería de los ingresos aprobados en el período</p>
                </div>
              </div>
            </div>

            {costoProveedores.length > 0 ? (
              <div className="p-5">
                <ResponsiveContainer width="100%" height={Math.max(180, datosCostoProveedor.length * 52)}>
                  <BarChart
                    data={datosCostoProveedor}
                    layout="vertical"
                    margin={{ left: 0, right: esMobile ? 10 : 30, top: 10, bottom: 10 }}
                    barGap={8}
                  >
                    <defs>
                      <linearGradient id="gradProveedorDefault" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.85} />
                        <stop offset="100%" stopColor="#047857" stopOpacity={1} />
                      </linearGradient>
                      <linearGradient id="gradProveedorSin" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#cbd5e1" stopOpacity={0.7} />
                        <stop offset="100%" stopColor="#94a3b8" stopOpacity={0.9} />
                      </linearGradient>
                      <filter id="provBarShadow" x="-5%" y="-15%" width="110%" height="130%">
                        <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.1" />
                      </filter>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis
                      type="number"
                      tickLine={false}
                      axisLine={{ stroke: "#e2e8f0" }}
                      tick={{ fill: "#94a3b8", fontSize: esMobile ? 11 : 12 }}
                      tickFormatter={(v) => `S/ ${v}`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={esMobile ? 85 : 130}
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: "#475569", fontSize: esMobile ? 11 : 12, fontWeight: 500 }}
                      interval={0}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const item = payload[0].payload;
                          return (
                            <div className="rounded-xl border border-zinc-200/80 bg-white/95 p-3.5 shadow-xl backdrop-blur-md">
                              <p className="text-xs font-semibold text-zinc-500">{item.nombreCompleto}</p>
                              <p className="mt-1 text-base font-extrabold text-zinc-900 tabular-nums">
                                S/ {Number(payload[0].value).toFixed(2)}
                              </p>
                              {totalCostoProveedores > 0 && (
                                <p className="mt-1.5 text-[11px] text-zinc-500 border-t border-zinc-100 pt-1.5">
                                  Representa el <span className="font-bold text-zinc-900">{((item.monto / totalCostoProveedores) * 100).toFixed(1)}%</span> del gasto total
                                </p>
                              )}
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar
                      dataKey="monto"
                      radius={[0, 10, 10, 0]}
                      maxBarSize={28}
                      filter="url(#provBarShadow)"
                    >
                      {datosCostoProveedor.map((d, i) => (
                        <Cell
                          key={i}
                          fill={
                            d.nombreCompleto === SIN_PROVEEDOR
                              ? "url(#gradProveedorSin)"
                              : "url(#gradProveedorDefault)"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>

                {/* Leyenda */}
                <div className="mt-4 flex flex-wrap items-center justify-center gap-5 border-t border-zinc-100 pt-3 text-xs font-medium text-zinc-500">
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-gradient-to-tr from-emerald-600 to-emerald-400 shadow-xs" />
                    <span>Con proveedor</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-gradient-to-tr from-slate-400 to-slate-300 shadow-xs" />
                    <span>Sin proveedor</span>
                  </div>
                </div>

                <div className="mt-4">
                  <Table
                    columnas={columnasCostoProveedor}
                    filas={costoProveedores}
                    claveDe={(c) => c.proveedor}
                  />
                </div>
              </div>
            ) : (
              <EmptyState
                icono={BarChart3}
                titulo="Sin ingresos aprobados"
                descripcion="No hubo ingresos de mercadería aprobados en el período."
              />
            )}
          </div>

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
                  <BarChart
                    data={datosTopProductos}
                    layout="vertical"
                    margin={{ left: 0, right: esMobile ? 10 : 20, top: 10, bottom: 10 }}
                  >
                    <defs>
                      <linearGradient id="gradTopProd" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.85} />
                        <stop offset="100%" stopColor="#4338ca" stopOpacity={1} />
                      </linearGradient>
                      <filter id="topProdShadow" x="-5%" y="-15%" width="110%" height="130%">
                        <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.1" />
                      </filter>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: esMobile ? 11 : 12 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={esMobile ? 85 : 125}
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: "#475569", fontSize: esMobile ? 11 : 12, fontWeight: 500 }}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const item = payload[0].payload;
                          return (
                            <div className="rounded-xl border border-zinc-200/80 bg-white/95 p-3.5 shadow-xl backdrop-blur-md">
                              <p className="text-xs font-semibold text-zinc-500">{item.nombreCompleto}</p>
                              <p className="mt-1 text-base font-extrabold text-zinc-900 tabular-nums">
                                {criterio === "unidades"
                                  ? `${item.cantidad} uds`
                                  : `S/ ${Number(item.total).toFixed(2)}`}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar
                      dataKey={criterio === "unidades" ? "cantidad" : "total"}
                      fill="url(#gradTopProd)"
                      radius={[0, 10, 10, 0]}
                      barSize={22}
                      filter="url(#topProdShadow)"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <Table
              // Va debajo del encabezado de la Card (y del gráfico), no al ras
              // del borde superior: sin redondeo arriba para no dejar un escalón.
              sinRedondeoSuperior
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
