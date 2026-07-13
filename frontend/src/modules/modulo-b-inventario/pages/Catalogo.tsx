// Página de catálogo de productos: consulta de stock y precios (ADMIN y CAJERO).
import { useState } from "react";
import { Package, Search } from "lucide-react";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { useProductos } from "../hooks/useProductos";
import type { Producto } from "../types";

function badgeDeStock(p: Producto) {
  if (p.stock <= 0) return <Badge tono="peligro">Sin stock</Badge>;
  if (p.stock <= p.stock_minimo) return <Badge tono="alerta">Stock bajo</Badge>;
  return <Badge tono="exito">Disponible</Badge>;
}

export default function Catalogo() {
  const { productos, cargando, error, noDisponible, recargar } = useProductos();
  const [busqueda, setBusqueda] = useState("");

  const columnas: Columna<Producto>[] = [
    { titulo: "Código", render: (p) => <span className="font-mono text-xs text-zinc-500">{p.codigo}</span> },
    { titulo: "Producto", render: (p) => <span className="font-medium text-zinc-800">{p.nombre}</span> },
    { titulo: "Categoría", soloEscritorio: true, render: (p) => p.categoria ?? "—" },
    {
      titulo: "Precio",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums">S/ {p.precio.toFixed(2)}</span>,
    },
    { titulo: "Stock", alinear: "derecha", render: (p) => <span className="tabular-nums">{p.stock}</span> },
    { titulo: "Estado", render: badgeDeStock },
  ];

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

  return (
    <div>
      <PageHeader titulo="Catálogo" descripcion="Stock y precios de todos los productos." />

      <div className="mb-4 max-w-sm">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" aria-hidden />
          <Input
            className="pl-9"
            placeholder="Buscar por nombre o código…"
            value={busqueda}
            onChange={(e) => {
              setBusqueda(e.target.value);
              void recargar(e.target.value || undefined);
            }}
          />
        </div>
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
        </Card>
      )}
    </div>
  );
}
