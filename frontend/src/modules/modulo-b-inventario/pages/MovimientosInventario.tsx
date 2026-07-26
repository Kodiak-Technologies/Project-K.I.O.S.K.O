// Bitácora de movimientos de inventario (ADMIN y CAJERO).
// Append-only: ingresos, mermas, ventas, devoluciones, ajustes.
import { useEffect, useState } from "react";
import { History as HistoryIcon } from "lucide-react";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { usePaginacionCursor } from "../../../shared/lib/use-paginacion-cursor";
import { PaginacionControles } from "../components/PaginacionControles";
import { SelectorProducto } from "../components/SelectorProducto";
import { useMovimientos } from "../hooks/useMovimientos";
import type { FiltrosMovimientos, MovimientoInventario, TipoMovimiento } from "../types";

const TONO_TIPO: Record<string, Tono> = {
  ingreso: "exito",
  merma: "peligro",
  venta: "info",
  devolucion: "alerta",
  ajuste: "neutro",
};

const TIPO_LABELS: Record<string, string> = {
  ingreso: "Ingreso",
  merma: "Merma",
  venta: "Venta",
  devolucion: "Devolución",
  ajuste: "Ajuste",
};

export default function MovimientosInventario() {
  const { movimientos, paginados, cargando, error, noDisponible, recargar } = useMovimientos();

  const [filtroProducto, setFiltroProducto] = useState<number | "">("");
  const [filtroTipo, setFiltroTipo] = useState<TipoMovimiento | "">("");
  const [fechaDesde, setFechaDesde] = useState<string>("");
  const [fechaHasta, setFechaHasta] = useState<string>("");
  // Cada venta escribe movimientos nuevos por arriba: con `page`/OFFSET las
  // filas se corrían y aparecían repetidas al pasar de página.
  const paginacion = usePaginacionCursor(20);
  const { page, pageSize, cursor, registrarRespuesta, reiniciar } = paginacion;

  // Otro filtro ⇒ otro conjunto: los cursores acumulados dejan de valer.
  useEffect(() => {
    reiniciar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroProducto, filtroTipo, fechaDesde, fechaHasta]);

  useEffect(() => {
    const filtros: FiltrosMovimientos = { page_size: pageSize };
    if (cursor) filtros.cursor = cursor;
    if (filtroProducto) filtros.producto_id = filtroProducto;
    if (filtroTipo) filtros.tipo = filtroTipo;
    if (fechaDesde) filtros.fecha_desde = fechaDesde;
    if (fechaHasta) filtros.fecha_hasta = fechaHasta;
    void recargar(filtros);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroProducto, filtroTipo, fechaDesde, fechaHasta, page, pageSize, cursor]);

  useEffect(() => {
    if (paginados) registrarRespuesta(paginados.siguiente_cursor);
  }, [paginados, registrarRespuesta]);

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Movimientos de inventario" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<MovimientoInventario>[] = [
    {
      titulo: "Fecha",
      render: (m) => (
        <span className="whitespace-nowrap text-zinc-500">
          {m.created_at ? new Date(m.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    { titulo: "Producto", render: (m) => m.producto_nombre ?? `#${m.producto_id}` },
    {
      titulo: "Tipo",
      render: (m) => {
        const t = String(m.tipo);
        return <Badge tono={TONO_TIPO[t] ?? "neutro"}>{TIPO_LABELS[t] ?? t}</Badge>;
      },
    },
    {
      titulo: "Cantidad",
      alinear: "derecha",
      render: (m) => (
        <span
          className={`tabular-nums font-medium ${
            m.cantidad > 0 ? "text-green-700" : "text-peligro"
          }`}
        >
          {m.cantidad > 0 ? "+" : ""}
          {m.cantidad}
        </span>
      ),
    },
    {
      titulo: "Motivo",
      soloEscritorio: true,
      render: (m) => m.motivo ?? "—",
    },
    {
      titulo: "Vinculado a",
      soloEscritorio: true,
      render: (m) => {
        if (m.solicitud_ingreso_id) return `Ingreso #${m.solicitud_ingreso_id}`;
        if (m.merma_id) return `Merma #${m.merma_id}`;
        return "—";
      },
    },
    { titulo: "Registró", soloEscritorio: true, render: (m) => m.registrado_por_nombre },
  ];

  return (
    <div>
      <PageHeader
        titulo="Movimientos de inventario"
        descripcion="Bitácora append-only de ingresos, mermas, ventas, devoluciones y ajustes."
      />

      <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Búsqueda contra el servidor: ver nota en Mermas.tsx. */}
        <SelectorProducto
          label="Producto"
          value={filtroProducto === "" ? null : filtroProducto}
          onChange={(id) => {
            setFiltroProducto(id ?? "");
          }}
          soloActivos={false}
        />
        <Select
          label="Tipo"
          value={filtroTipo}
          onChange={(e) => {
            setFiltroTipo(e.target.value as TipoMovimiento | "");
          }}
        >
          <option value="">Todos</option>
          <option value="ingreso">Ingreso</option>
          <option value="merma">Merma</option>
          <option value="venta">Venta</option>
          <option value="devolucion">Devolución</option>
          <option value="ajuste">Ajuste</option>
        </Select>
        <div>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-zinc-700">Desde</span>
            <input
              type="date"
              value={fechaDesde}
              onChange={(e) => {
                setFechaDesde(e.target.value);
              }}
              className="w-full min-h-tactil rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-zinc-500"
            />
          </label>
        </div>
        <div>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-zinc-700">Hasta</span>
            <input
              type="date"
              value={fechaHasta}
              onChange={(e) => {
                setFechaHasta(e.target.value);
              }}
              className="w-full min-h-tactil rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-zinc-500"
            />
          </label>
        </div>
      </div>

      {cargando && movimientos.length === 0 ? (
        <PageSpinner texto="Cargando movimientos…" />
      ) : error ? (
        <Alert tono="peligro">{error}</Alert>
      ) : (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={movimientos}
            claveDe={(m) => m.id}
            vacio={
              <EmptyState
                icono={HistoryIcon}
                titulo="Sin movimientos"
                descripcion="Cuando registres ingresos, mermas o ventas, aparecerán acá."
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={paginacion.onCambiarPage}
            onCambiarPageSize={paginacion.onCambiarPageSize}
            etiqueta="movimientos"
          />
        </Card>
      )}
    </div>
  );
}
