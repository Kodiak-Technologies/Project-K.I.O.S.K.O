// Bitácora de movimientos de inventario (ADMIN y CAJERO).
// Append-only: ingresos, ventas, devoluciones y ajustes de stock.
import { useEffect, useState } from "react";
import { History as HistoryIcon } from "lucide-react";
import {
  Alert,
  Badge,
  Card,
  DatePicker,
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
  venta: "info",
  devolucion: "alerta",
  ajuste: "neutro",
};

const TIPO_LABELS: Record<string, string> = {
  ingreso: "Ingreso",
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
      ancho: "175px",
      render: (m) => (
        <span className="whitespace-nowrap text-zinc-500">
          {m.created_at ? new Date(m.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Producto",
      ancho: "160px",
      render: (m) => <span className="font-medium text-zinc-800 truncate block" title={m.producto_nombre ?? `#${m.producto_id}`}>{m.producto_nombre ?? `#${m.producto_id}`}</span>,
    },
    {
      titulo: "Tipo",
      ancho: "110px",
      render: (m) => {
        const t = String(m.tipo);
        return <Badge tono={TONO_TIPO[t] ?? "neutro"}>{TIPO_LABELS[t] ?? t}</Badge>;
      },
    },
    {
      titulo: "Cantidad",
      ancho: "90px",
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
      ancho: "150px",
      soloEscritorio: true,
      render: (m) => <span className="truncate block" title={m.motivo ?? "—"}>{m.motivo ?? "—"}</span>,
    },
    {
      titulo: "Vinculado a",
      ancho: "120px",
      soloEscritorio: true,
      render: (m) => {
        if (m.solicitud_ingreso_id) return `Ingreso #${m.solicitud_ingreso_id}`;
        return "—";
      },
    },
    {
      titulo: "Registró",
      soloEscritorio: true,
      render: (m) => <span className="font-medium text-zinc-800">{m.registrado_por_nombre}</span>,
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Movimientos de inventario"
        descripcion="Bitácora append-only de ingresos, ventas, devoluciones y ajustes de stock."
      />

      <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Búsqueda contra el servidor: no carga el catálogo entero. */}
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
          <option value="venta">Venta</option>
          <option value="devolucion">Devolución</option>
          <option value="ajuste">Ajuste</option>
        </Select>
        <DatePicker
          label="Desde"
          mostrarAnio
          value={fechaDesde}
          onChange={(val) => setFechaDesde(val)}
        />
        <DatePicker
          label="Hasta"
          mostrarAnio
          value={fechaHasta}
          onChange={(val) => setFechaHasta(val)}
        />
      </div>

      {cargando && movimientos.length === 0 ? (
        <PageSpinner texto="Cargando movimientos…" />
      ) : error ? (
        <Alert tono="peligro">{error}</Alert>
      ) : (
        <Card sinPadding>
          <Table
            minAncho="100%"
            columnas={columnas}
            filas={movimientos}
            claveDe={(m) => m.id}
            vacio={
              <EmptyState
                icono={HistoryIcon}
                titulo="Sin movimientos"
                descripcion="Cuando registres ingresos, ventas o ajustes, aparecerán acá."
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
