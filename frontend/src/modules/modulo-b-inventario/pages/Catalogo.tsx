// Página de catálogo de productos: consulta de stock y precios (ADMIN y CAJERO).
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Package, Search, Truck } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { PaginacionControles } from "../components/PaginacionControles";
import { useProductos } from "../hooks/useProductos";
import type { FiltrosProductos, Producto } from "../types";

const DEBOUNCE_MS = 300;

function badgeDeStock(p: Producto) {
  if (p.stock <= 0) return <Badge tono="peligro">Sin stock</Badge>;
  if (p.stock <= p.stock_minimo) return <Badge tono="alerta">Bajo stock</Badge>;
  return <Badge tono="exito">Disponible</Badge>;
}

const TONO_FILTRO_STOCK: Record<string, Tono> = {
  disponibles: "exito",
  bajo_minimo: "alerta",
  sin_stock: "peligro",
};

export default function Catalogo() {
  const { productos, paginados, cargando, error, noDisponible, recargar } = useProductos();
  const [busqueda, setBusqueda] = useState("");
  const [filtroStock, setFiltroStock] = useState<"todos" | "disponibles" | "bajo_minimo" | "sin_stock">(
    "todos",
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const navigate = useNavigate();

  // Debounce del search.
  useEffect(() => {
    const handle = window.setTimeout(() => {
      const filtros: FiltrosProductos = { page, page_size: pageSize };
      if (busqueda.trim()) filtros.search = busqueda.trim();
      if (filtroStock === "disponibles") filtros.solo_con_stock = true;
      if (filtroStock === "bajo_minimo") filtros.solo_bajo_minimo = true;
      // "sin_stock" no es un flag del backend; lo pedimos como "solo bajo mínimo" (incluye 0).
      if (filtroStock === "sin_stock") filtros.solo_bajo_minimo = true;
      void recargar(filtros);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busqueda, filtroStock, page, pageSize]);

  function irAReponer(productoId: number) {
    navigate(`/ingresos?producto_id=${productoId}`);
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Catálogo" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Producto>[] = [
    {
      titulo: "Foto",
      render: (p) =>
        p.foto_url ? (
          <img src={p.foto_url} alt={p.nombre} className="h-8 w-8 rounded object-cover" />
        ) : (
          <div className="h-8 w-8 rounded bg-zinc-100" aria-hidden />
        ),
    },
    { titulo: "Código", render: (p) => <span className="font-mono text-xs text-zinc-500">{p.codigo}</span> },
    { titulo: "Producto", render: (p) => <span className="font-medium text-zinc-800">{p.nombre}</span> },
    { titulo: "Categoría", soloEscritorio: true, render: (p) => p.categoria_nombre ?? "—" },
    {
      titulo: "Precio",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums">S/ {(p.precio_venta ?? p.precio).toFixed(2)}</span>,
    },
    { titulo: "Stock", alinear: "derecha", render: (p) => <span className="tabular-nums">{p.stock}</span> },
    { titulo: "Estado", render: badgeDeStock },
    {
      titulo: "Acciones",
      render: (p) =>
        p.stock <= p.stock_minimo ? (
          <Button
            compacto
            variante="secundario"
            icono={<Truck className="h-4 w-4" aria-hidden />}
            onClick={() => irAReponer(p.id)}
            title="Reponer stock"
          >
            Reponer
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <PageHeader titulo="Catálogo" descripcion="Stock y precios de todos los productos." />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="relative min-w-64 flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" aria-hidden />
          <Input
            className="pl-9"
            placeholder="Buscar por nombre o código…"
            value={busqueda}
            onChange={(e) => {
              setBusqueda(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          aria-label="Filtrar por stock"
          value={filtroStock}
          onChange={(e) => {
            setFiltroStock(e.target.value as typeof filtroStock);
            setPage(1);
          }}
          className="max-w-xs"
        >
          <option value="todos">Todos</option>
          <option value="disponibles">Con stock</option>
          <option value="bajo_minimo">Bajo mínimo</option>
          <option value="sin_stock">Sin stock</option>
        </Select>
        {filtroStock !== "todos" && (
          <Badge tono={TONO_FILTRO_STOCK[filtroStock] ?? "neutro"}>{filtroStock.replace("_", " ")}</Badge>
        )}
      </div>

      {cargando && <PageSpinner texto="Cargando catálogo…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={productos}
            claveDe={(p) => p.id}
            vacio={
              <EmptyState
                icono={Package}
                titulo="Sin productos"
                descripcion={busqueda ? "Nada coincide con tu búsqueda." : "El catálogo está vacío."}
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={setPageSize}
            etiqueta="productos"
          />
        </Card>
      )}
    </div>
  );
}
