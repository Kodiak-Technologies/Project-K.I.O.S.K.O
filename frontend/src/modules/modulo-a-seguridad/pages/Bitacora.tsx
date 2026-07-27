import { useState } from "react";
import { FileText, ScrollText } from "lucide-react";
import {
  Alert,
  Badge,
  Card,
  DateTimePicker,
  EmptyState,
  Input,
  Modal,
  PageHeader,
  PageSpinner,
  PaginacionControles,
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { useBitacora } from "../hooks/useBitacora";
import type { RegistroBitacora } from "../types";

function tonoDeAccion(accion: string): Tono {
  if (accion.includes("fallido") || accion.includes("bloque")) return "peligro";
  if (accion.includes("elimina") || accion.includes("anula")) return "alerta";
  if (accion.includes("exitoso") || accion.includes("crea")) return "exito";
  return "neutro";
}

export default function Bitacora() {
  const { datos, filtros, cargando, error, aplicarFiltros } = useBitacora();
  const [detalleModal, setDetalleModal] = useState<RegistroBitacora | null>(null);

  const pagina = filtros.pagina ?? 1;
  const tamanoPagina = filtros.tamano_pagina ?? 25;
  const totalPaginas = datos ? Math.max(1, Math.ceil(datos.total / tamanoPagina)) : 1;

  const paginados = datos
    ? {
      total: datos.total,
      total_pages: totalPaginas,
    }
    : null;

  const columnas: Columna<RegistroBitacora>[] = [
    {
      titulo: "Fecha",
      ancho: "185px",
      render: (r) => (
        <span className="whitespace-nowrap text-zinc-500">
          {r.created_at ? new Date(r.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    { titulo: "Usuario", ancho: "80px", render: (r) => r.usuario_id ?? "—" },
    { titulo: "Rol", ancho: "90px", soloEscritorio: true, render: (r) => r.rol || "—" },
    { titulo: "Acción", ancho: "180px", render: (r) => <Badge tono={tonoDeAccion(r.accion)}>{r.accion}</Badge> },
    { titulo: "Entidad", ancho: "140px", render: (r) => `${r.entidad}${r.entidad_id ? ` #${r.entidad_id}` : ""}` },
    {
      titulo: "Detalle",
      ancho: "80px",
      alinear: "centro",
      render: (r) => {
        const tieneDetalle = Boolean(r.motivo || r.valor_anterior || r.valor_nuevo);
        if (!tieneDetalle) {
          return (
            <div className="flex justify-center">
              <span className="inline-flex items-center justify-center rounded-lg p-1.5 text-zinc-300" title="Sin detalle">
                <FileText className="h-4 w-4" />
              </span>
            </div>
          );
        }
        return (
          <div className="flex justify-center">
            <button
              type="button"
              onClick={() => setDetalleModal(r)}
              className="inline-flex items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 p-1.5 text-emerald-600 transition-colors hover:bg-emerald-100 hover:text-emerald-700 shadow-sm"
              title="Ver detalle del registro"
            >
              <FileText className="h-4 w-4" />
            </button>
          </div>
        );
      },
    },
    {
      titulo: "IP",
      ancho: "140px",
      soloEscritorio: true,
      render: (r) => <span className="whitespace-nowrap font-mono text-xs text-zinc-500">{r.ip || "—"}</span>,
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Bitácora de auditoría"
        descripcion="Registro inmutable de todo lo que pasa en el sistema."
      />

      <Card className="mb-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1.5fr_1.5fr_1fr_1fr_1fr]">
          <DateTimePicker
            label="Desde"
            value={filtros.desde}
            onChange={(val) => aplicarFiltros({ desde: val })}
          />
          <DateTimePicker
            label="Hasta"
            value={filtros.hasta}
            onChange={(val) => aplicarFiltros({ hasta: val })}
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

      {cargando && !datos && <PageSpinner texto="Consultando bitácora…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {datos && (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={datos.registros}
            claveDe={(r) => r.id}
            contenedorClassName="max-h-[calc(100vh-27rem)] lg:max-h-[calc(100vh-26rem)]"
            vacio={
              <EmptyState
                icono={ScrollText}
                titulo="Sin registros"
                descripcion="No hay eventos para los filtros elegidos."
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={pagina}
            pageSize={tamanoPagina}
            onCambiarPage={(p) => aplicarFiltros({ pagina: p })}
            onCambiarPageSize={(s) => aplicarFiltros({ tamano_pagina: s, pagina: 1 })}
            etiqueta="registros"
          />
        </Card>
      )}

      {detalleModal && (
        <Modal
          titulo={`Detalle de auditoría #${detalleModal.id}`}
          abierto={Boolean(detalleModal)}
          alCerrar={() => setDetalleModal(null)}
        >
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-3 rounded-lg border border-zinc-100 bg-zinc-50 p-3">
              <div>
                <span className="block text-xs font-medium text-zinc-400">Acción</span>
                <span className="font-semibold text-zinc-800">{detalleModal.accion}</span>
              </div>
              <div>
                <span className="block text-xs font-medium text-zinc-400">Entidad</span>
                <span className="font-semibold text-zinc-800">
                  {detalleModal.entidad} {detalleModal.entidad_id ? `#${detalleModal.entidad_id}` : ""}
                </span>
              </div>
              <div>
                <span className="block text-xs font-medium text-zinc-400">Fecha</span>
                <span className="text-zinc-700">
                  {detalleModal.created_at ? new Date(detalleModal.created_at).toLocaleString("es-PE") : "—"}
                </span>
              </div>
              <div>
                <span className="block text-xs font-medium text-zinc-400">IP</span>
                <span className="font-mono text-zinc-700">{detalleModal.ip || "—"}</span>
              </div>
            </div>

            {detalleModal.motivo && (
              <div>
                <h4 className="mb-1 text-xs font-semibold text-zinc-700">Motivo / Observación</h4>
                <p className="rounded-lg border border-zinc-200 bg-white p-2.5 text-zinc-800">
                  {detalleModal.motivo}
                </p>
              </div>
            )}

            {detalleModal.valor_anterior && (
              <div>
                <h4 className="mb-1 text-xs font-semibold text-zinc-500">Valor Anterior</h4>
                <pre className="max-h-48 overflow-auto rounded-lg border border-zinc-200 bg-zinc-900 p-3 text-xs font-mono text-zinc-100">
                  {JSON.stringify(detalleModal.valor_anterior, null, 2)}
                </pre>
              </div>
            )}

            {detalleModal.valor_nuevo && (
              <div>
                <h4 className="mb-1 text-xs font-semibold text-emerald-700">Valor Nuevo</h4>
                <pre className="max-h-48 overflow-auto rounded-lg border border-emerald-200 bg-zinc-900 p-3 text-xs font-mono text-emerald-400">
                  {JSON.stringify(detalleModal.valor_nuevo, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
