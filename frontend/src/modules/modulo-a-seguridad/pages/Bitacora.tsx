// Página de consulta de la bitácora (solo ADMIN): filtros por fecha, usuario,
// acción y entidad, con paginación. Objetivo: hallar quién hizo qué en < 1 minuto.
import { ChevronLeft, ChevronRight, ScrollText } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { useBitacora } from "../hooks/useBitacora";
import type { RegistroBitacora } from "../types";

/** El tono del badge comunica la severidad de la acción de un vistazo. */
function tonoDeAccion(accion: string): Tono {
  if (accion.includes("fallido") || accion.includes("bloque")) return "peligro";
  if (accion.includes("elimina") || accion.includes("anula")) return "alerta";
  if (accion.includes("exitoso") || accion.includes("crea")) return "exito";
  return "neutro";
}

export default function Bitacora() {
  const { datos, filtros, cargando, error, aplicarFiltros } = useBitacora();

  const totalPaginas = datos ? Math.max(1, Math.ceil(datos.total / (filtros.tamano_pagina ?? 25))) : 1;
  const pagina = filtros.pagina ?? 1;

  const columnas: Columna<RegistroBitacora>[] = [
    {
      titulo: "Fecha",
      render: (r) => (
        <span className="whitespace-nowrap text-zinc-500">
          {r.created_at ? new Date(r.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    { titulo: "Usuario", render: (r) => r.usuario_id ?? "—" },
    { titulo: "Rol", soloEscritorio: true, render: (r) => r.rol || "—" },
    { titulo: "Acción", render: (r) => <Badge tono={tonoDeAccion(r.accion)}>{r.accion}</Badge> },
    { titulo: "Entidad", render: (r) => `${r.entidad}${r.entidad_id ? ` #${r.entidad_id}` : ""}` },
    {
      titulo: "Detalle",
      render: (r) => (
        <div className="max-w-xs text-xs text-zinc-600">
          {r.motivo && <p>{r.motivo}</p>}
          {r.valor_anterior && (
            <p className="truncate" title={JSON.stringify(r.valor_anterior)}>
              Antes: {JSON.stringify(r.valor_anterior)}
            </p>
          )}
          {r.valor_nuevo && (
            <p className="truncate" title={JSON.stringify(r.valor_nuevo)}>
              Después: {JSON.stringify(r.valor_nuevo)}
            </p>
          )}
        </div>
      ),
    },
    { titulo: "IP", soloEscritorio: true, render: (r) => <span className="text-zinc-500">{r.ip || "—"}</span> },
  ];

  return (
    <div>
      <PageHeader
        titulo="Bitácora de auditoría"
        descripcion="Registro inmutable de todo lo que pasa en el sistema."
      />

      <Card className="mb-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Input
            label="Desde"
            type="datetime-local"
            onChange={(e) => aplicarFiltros({ desde: e.target.value || undefined })}
          />
          <Input
            label="Hasta"
            type="datetime-local"
            onChange={(e) => aplicarFiltros({ hasta: e.target.value || undefined })}
          />
          <Input
            label="ID de usuario"
            type="number"
            min={1}
            placeholder="ej. 3"
            onChange={(e) => aplicarFiltros({ usuario_id: e.target.value ? Number(e.target.value) : undefined })}
          />
          <Input
            label="Acción"
            placeholder="ej. login_fallido"
            onChange={(e) => aplicarFiltros({ accion: e.target.value || undefined })}
          />
          <Input
            label="Entidad"
            placeholder="ej. usuarios, ventas"
            onChange={(e) => aplicarFiltros({ entidad: e.target.value || undefined })}
          />
        </div>
      </Card>

      {cargando && <PageSpinner texto="Consultando bitácora…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {datos && !cargando && (
        <>
          <Card sinPadding>
            <Table
              columnas={columnas}
              filas={datos.registros}
              claveDe={(r) => r.id}
              vacio={
                <EmptyState
                  icono={ScrollText}
                  titulo="Sin registros"
                  descripcion="No hay eventos para los filtros elegidos."
                />
              }
            />
          </Card>

          <div className="mt-3 flex items-center justify-between text-sm text-zinc-600">
            <span>
              {datos.total} registro(s) — página {pagina} de {totalPaginas}
            </span>
            <div className="flex gap-2">
              <Button
                variante="secundario"
                compacto
                disabled={pagina <= 1}
                onClick={() => aplicarFiltros({ pagina: pagina - 1 })}
                icono={<ChevronLeft className="h-4 w-4" aria-hidden />}
              >
                Anterior
              </Button>
              <Button
                variante="secundario"
                compacto
                disabled={pagina >= totalPaginas}
                onClick={() => aplicarFiltros({ pagina: pagina + 1 })}
              >
                Siguiente
                <ChevronRight className="h-4 w-4" aria-hidden />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
