import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";
import {
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  Percent,
  Sparkles,
  PieChart as PieChartIcon,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

interface GraficoVentasEgresosProps {
  totalVendido: number;
  totalEgresos: number;
  totalDevuelto?: number;
  numeroVentas?: number;
}

export function GraficoVentasEgresos({
  totalVendido,
  totalEgresos,
  totalDevuelto = 0,
}: GraficoVentasEgresosProps) {
  const [incluirUtilidad, setIncluirUtilidad] = useState(true);
  const [hoveredBar, setHoveredBar] = useState<string | null>(null);

  const utilidadNeta = totalVendido - totalEgresos;
  const margenPorcentaje =
    totalVendido > 0 ? ((utilidadNeta / totalVendido) * 100).toFixed(1) : "0.0";
  const egresosPorcentaje =
    totalVendido > 0 ? ((totalEgresos / totalVendido) * 100).toFixed(1) : "0.0";
  const esRentable = utilidadNeta >= 0;

  const data = [
    {
      categoria: "Comparativa del Período",
      ventas: totalVendido,
      egresos: totalEgresos,
      ...(incluirUtilidad ? { utilidad: Math.max(0, utilidadNeta) } : {}),
    },
  ];

  const dataDesglosada = [
    {
      name: "Venta Total",
      monto: totalVendido,
      colorStart: "#10b981",
      colorEnd: "#047857",
      gradId: "gradVentas",
      tipo: "ventas",
      icon: ArrowUpRight,
      pct: 100,
    },
    {
      name: "Egresos Totales",
      monto: totalEgresos,
      colorStart: "#f43f5e",
      colorEnd: "#be123c",
      gradId: "gradEgresos",
      tipo: "egresos",
      icon: ArrowDownRight,
      pct: totalVendido > 0 ? (totalEgresos / totalVendido) * 100 : 0,
    },
    ...(incluirUtilidad
      ? [
          {
            name: "Utilidad Neta",
            monto: Math.max(0, utilidadNeta),
            colorStart: "#6366f1",
            colorEnd: "#4338ca",
            gradId: "gradUtilidad",
            tipo: "utilidad",
            icon: Sparkles,
            pct: totalVendido > 0 ? (utilidadNeta / totalVendido) * 100 : 0,
          },
        ]
      : []),
  ];

  const formatSoles = (val: number) => `S/ ${val.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-sm transition-all duration-300 hover:shadow-md">
      {/* Header del Gráfico */}
      <div className="border-b border-zinc-100 bg-gradient-to-r from-zinc-50/80 via-white to-zinc-50/50 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 shadow-inner">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-zinc-900">Rendimiento Financiero</h3>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-200/60">
                  <TrendingUp className="h-3 w-3" />
                  Ventas vs Egresos
                </span>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">
                Balance de flujo de caja y margen de utilidad del período seleccionado
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIncluirUtilidad(!incluirUtilidad)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                incluirUtilidad
                  ? "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {incluirUtilidad ? "Utilidad Visible" : "Mostrar Utilidad"}
            </button>
          </div>
        </div>

        {/* Tarjetas de Métricas Ejecutivas */}
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {/* Ingresos / Ventas */}
          <div className="relative overflow-hidden rounded-xl border border-emerald-100 bg-gradient-to-br from-emerald-50/60 via-white to-emerald-50/30 p-3.5 transition-transform hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-emerald-800">Venta Total</span>
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <ArrowUpRight className="h-3.5 w-3.5" />
              </span>
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-xl font-extrabold text-emerald-950 tabular-nums">
                {formatSoles(totalVendido)}
              </span>
              <span className="text-[11px] font-semibold text-emerald-600">100% flujo</span>
            </div>
            {totalDevuelto > 0 && (
              <p className="mt-1 text-[10px] text-zinc-400">
                Devoluciones: S/ {totalDevuelto.toFixed(2)} (ya deducido)
              </p>
            )}
          </div>

          {/* Egresos */}
          <div className="relative overflow-hidden rounded-xl border border-rose-100 bg-gradient-to-br from-rose-50/60 via-white to-rose-50/30 p-3.5 transition-transform hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-rose-800">Egresos / Gastos</span>
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-rose-100 text-rose-600">
                <ArrowDownRight className="h-3.5 w-3.5" />
              </span>
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-xl font-extrabold text-rose-950 tabular-nums">
                {formatSoles(totalEgresos)}
              </span>
              <span className="text-[11px] font-semibold text-rose-600">
                {egresosPorcentaje}% ventas
              </span>
            </div>
            <p className="mt-1 text-[10px] text-zinc-400">
              Costo de mercadería y gastos
            </p>
          </div>

          {/* Utilidad / Margen */}
          <div
            className={`relative overflow-hidden rounded-xl border p-3.5 transition-transform hover:-translate-y-0.5 ${
              esRentable
                ? "border-indigo-100 bg-gradient-to-br from-indigo-50/60 via-white to-indigo-50/30 text-indigo-950"
                : "border-amber-100 bg-gradient-to-br from-amber-50/60 via-white to-amber-50/30 text-amber-950"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium">Utilidad Neta</span>
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  esRentable ? "bg-indigo-100 text-indigo-600" : "bg-amber-100 text-amber-600"
                }`}
              >
                {esRentable ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5" />
                )}
              </span>
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-xl font-extrabold tabular-nums">
                {formatSoles(utilidadNeta)}
              </span>
              <span
                className={`inline-flex items-center gap-0.5 text-[11px] font-semibold ${
                  esRentable ? "text-indigo-600" : "text-amber-600"
                }`}
              >
                <Percent className="h-3 w-3" />
                {margenPorcentaje}% margen
              </span>
            </div>
            <p className="mt-1 text-[10px] text-zinc-400">
              {esRentable ? "Ganancia disponible en período" : "Alerta de egresos superados"}
            </p>
          </div>
        </div>

        {/* Barra de Proporción / Visual Ratio Meter */}
        {totalVendido > 0 && (
          <div className="mt-4 rounded-xl border border-zinc-200/60 bg-white p-3 shadow-2xs">
            <div className="flex items-center justify-between text-xs font-medium text-zinc-600">
              <span className="flex items-center gap-1.5">
                <PieChartIcon className="h-3.5 w-3.5 text-zinc-400" />
                Distribución de los Ingresos
              </span>
              <span className="text-zinc-500 text-[11px]">
                Egresos ({egresosPorcentaje}%) | Ganancia Neta ({margenPorcentaje}%)
              </span>
            </div>

            <div className="mt-2 flex h-3 w-full overflow-hidden rounded-full bg-zinc-100 p-0.5 shadow-inner">
              {/* Parte Egresos */}
              <div
                style={{ width: `${Math.min(100, Math.max(0, Number(egresosPorcentaje)))}%` }}
                className="h-full rounded-l-full bg-gradient-to-r from-rose-500 to-rose-400 transition-all duration-500"
                title={`Egresos: ${egresosPorcentaje}%`}
              />
              {/* Parte Utilidad */}
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, Number(margenPorcentaje)))}%`,
                }}
                className="h-full rounded-r-full bg-gradient-to-r from-emerald-500 via-indigo-500 to-indigo-600 transition-all duration-500"
                title={`Utilidad Neta: ${margenPorcentaje}%`}
              />
            </div>
          </div>
        )}
      </div>

      {/* Área del Gráfico Principal con Recharts */}
      <div className="p-6">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={dataDesglosada}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
              barGap={12}
            >
              {/* Defs para Gradientes SVG de Alto Impacto */}
              <defs>
                <linearGradient id="gradVentas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={1} />
                  <stop offset="100%" stopColor="#047857" stopOpacity={0.85} />
                </linearGradient>
                <linearGradient id="gradEgresos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f43f5e" stopOpacity={1} />
                  <stop offset="100%" stopColor="#be123c" stopOpacity={0.85} />
                </linearGradient>
                <linearGradient id="gradUtilidad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={1} />
                  <stop offset="100%" stopColor="#4338ca" stopOpacity={0.85} />
                </linearGradient>
                <filter id="barShadow" x="-10%" y="-10%" width="120%" height="120%">
                  <feDropShadow dx="0" dy="4" stdDeviation="4" floodOpacity="0.15" />
                </filter>
              </defs>

              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="name"
                tickLine={false}
                axisLine={{ stroke: "#e2e8f0" }}
                tick={{ fill: "#64748b", fontSize: 13, fontWeight: 500 }}
                dy={8}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
                tickFormatter={(val) => `S/ ${val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val}`}
              />

              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const item = payload[0].payload;
                    const Icon = item.icon;
                    return (
                      <div className="rounded-xl border border-zinc-200/80 bg-white/95 p-3.5 shadow-xl backdrop-blur-md">
                        <div className="flex items-center gap-2">
                          <div
                            className="flex h-7 w-7 items-center justify-center rounded-lg text-white"
                            style={{ backgroundColor: item.colorStart }}
                          >
                            <Icon className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-zinc-500">{item.name}</p>
                            <p className="text-base font-extrabold text-zinc-900">
                              {formatSoles(item.monto)}
                            </p>
                          </div>
                        </div>
                        {totalVendido > 0 && (
                          <div className="mt-2 border-t border-zinc-100 pt-2 text-[11px] text-zinc-600">
                            Equivale al <span className="font-bold text-zinc-900">{item.pct.toFixed(1)}%</span> de los ingresos del período.
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />

              <Bar
                dataKey="monto"
                radius={[12, 12, 4, 4]}
                maxBarSize={64}
                animationDuration={1000}
                filter="url(#barShadow)"
                onMouseEnter={(entry) => setHoveredBar(entry?.name ?? null)}
                onMouseLeave={() => setHoveredBar(null)}
              >
                {dataDesglosada.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={`url(#${entry.gradId})`}
                    stroke={hoveredBar === entry.name ? "#000" : "none"}
                    strokeWidth={hoveredBar === entry.name ? 1.5 : 0}
                    style={{ cursor: "pointer", transition: "opacity 0.2s ease" }}
                    opacity={hoveredBar && hoveredBar !== entry.name ? 0.6 : 1}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Leyenda Personalizada e Interactiva */}
        <div className="mt-4 flex flex-wrap items-center justify-center gap-6 border-t border-zinc-100 pt-4 text-xs font-medium text-zinc-600">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-gradient-to-tr from-emerald-600 to-emerald-400 shadow-xs" />
            <span>Ingresos (Ventas)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-gradient-to-tr from-rose-600 to-rose-400 shadow-xs" />
            <span>Egresos (Gastos)</span>
          </div>
          {incluirUtilidad && (
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-400 shadow-xs" />
              <span>Utilidad Neta</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
