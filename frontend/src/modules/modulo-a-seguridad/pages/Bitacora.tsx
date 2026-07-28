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
  Select,
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

// La bitácora la lee la administradora, no un programador: los códigos internos
// que guarda el backend (`login_fallido`, `solicitudes_ingreso`, `precio_venta`)
// se traducen a lenguaje corriente antes de mostrarse.
const TEXTO_ACCION: Record<string, string> = {
  login_exitoso: "Inició sesión",
  login_fallido: "Intento de inicio de sesión fallido",
  login_rechazado_bloqueo: "Inicio de sesión rechazado por bloqueo",
  logout: "Cerró sesión",
  cuenta_bloqueada: "Cuenta bloqueada",
  password_cambiada: "Cambió su contraseña",
  password_reseteada: "Restableció una contraseña",
  permisos_modificados: "Modificó permisos",
  usuario_creado: "Creó un usuario",
  usuario_editado: "Editó un usuario",
  usuario_activado: "Activó un usuario",
  usuario_eliminado: "Eliminó un usuario",
  configuracion_actualizada: "Actualizó la configuración",
  producto_creado: "Creó un producto",
  producto_editado: "Editó un producto",
  producto_eliminado: "Eliminó un producto",
  categoria_creada: "Creó una categoría",
  categoria_editada: "Editó una categoría",
  cambiar_precio: "Cambió un precio",
  ajustar_stock: "Ajustó el stock",
  ingreso_solicitado: "Solicitó un ingreso de mercadería",
  editar_ingreso: "Editó una solicitud de ingreso",
  aprobar_ingreso: "Aprobó un ingreso de mercadería",
  rechazar_ingreso: "Rechazó un ingreso de mercadería",
  proveedor_creado: "Creó un proveedor",
  proveedor_editado: "Editó un proveedor",
  compra_credito: "Registró una compra a crédito",
  pago_proveedor: "Registró un pago a proveedor",
  metodo_pago_creado: "Creó un método de pago",
  metodo_pago_editado: "Editó un método de pago",
  venta_registrada: "Registró una venta",
  venta_anulada: "Anuló una venta",
  venta_devuelta: "Registró una devolución",
  caja_abierta: "Abrió la caja",
  caja_cerrada: "Cerró la caja",
  caja_descuadre: "Descuadre de caja",
  storage_upload: "Subió una imagen",
};

const TEXTO_ENTIDAD: Record<string, string> = {
  usuarios: "Usuarios",
  roles: "Roles",
  configuracion_negocio: "Configuración del negocio",
  productos: "Productos",
  categorias: "Categorías",
  proveedores: "Proveedores",
  solicitudes_ingreso: "Ingresos de mercadería",
  metodos_pago: "Métodos de pago",
  ventas: "Ventas",
  turnos_caja: "Caja",
  storage: "Imágenes",
};

const TEXTO_CAMPO: Record<string, string> = {
  precio_venta: "Precio de venta",
  precio_compra_actual: "Precio de compra",
  stock_actual: "Stock",
  stock_minimo: "Stock mínimo",
  razon_social: "Razón social",
  metodo_pago: "Método de pago",
  entidad_id: "N.° de registro",
};

/** Fallback para códigos nuevos que todavía no están en los mapas de arriba. */
function humanizar(codigo: string): string {
  const texto = codigo.replace(/_/g, " ").trim();
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Opciones de filtro: la administradora elige el texto, el backend recibe el código. */
const opcionesDe = (mapa: Record<string, string>) =>
  [{ value: "", label: "Todas" }].concat(
    Object.entries(mapa)
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label, "es"))
  );

const OPCIONES_ACCION = opcionesDe(TEXTO_ACCION);
const OPCIONES_ENTIDAD = opcionesDe(TEXTO_ENTIDAD);

const textoAccion = (accion: string) => TEXTO_ACCION[accion] ?? humanizar(accion);
const textoEntidad = (entidad: string) => TEXTO_ENTIDAD[entidad] ?? humanizar(entidad);
const textoCampo = (campo: string) => TEXTO_CAMPO[campo] ?? humanizar(campo);

function textoValor(valor: unknown): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (typeof valor === "object") return JSON.stringify(valor);
  return String(valor);
}

/** Muestra el contenido de un cambio como "campo: valor", nunca como JSON. */
function DetalleValores({ titulo, valores }: { titulo: string; valores: Record<string, unknown> }) {
  const entradas = Object.entries(valores);
  if (entradas.length === 0) return null;
  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold text-zinc-700">{titulo}</h4>
      <dl className="divide-y divide-zinc-100 rounded-lg border border-zinc-200 bg-white">
        {entradas.map(([campo, valor]) => (
          <div key={campo} className="flex gap-3 px-2.5 py-1.5">
            <dt className="w-40 shrink-0 text-xs text-zinc-500">{textoCampo(campo)}</dt>
            <dd className="min-w-0 flex-1 break-words text-zinc-800">{textoValor(valor)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
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
    {
      titulo: "Acción",
      ancho: "230px",
      render: (r) => <Badge tono={tonoDeAccion(r.accion)}>{textoAccion(r.accion)}</Badge>,
    },
    {
      titulo: "Sección",
      ancho: "170px",
      render: (r) => `${textoEntidad(r.entidad)}${r.entidad_id ? ` n.° ${r.entidad_id}` : ""}`,
    },
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
              className="inline-flex min-h-tactil min-w-11 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 p-1.5 text-emerald-600 shadow-sm transition-colors hover:bg-emerald-100 hover:text-emerald-700 sm:min-h-0 sm:min-w-0"
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
            label="N.° de usuario"
            type="number"
            min={1}
            placeholder="ej. 3"
            onChange={(e) => aplicarFiltros({ usuario_id: e.target.value ? Number(e.target.value) : undefined })}
          />
          <Select
            label="Acción"
            placeholder="Todas las acciones"
            buscable
            value={filtros.accion ?? ""}
            opciones={OPCIONES_ACCION}
            onChange={(e) => aplicarFiltros({ accion: e.target.value || undefined })}
          />
          <Select
            label="Sección"
            placeholder="Todas las secciones"
            value={filtros.entidad ?? ""}
            opciones={OPCIONES_ENTIDAD}
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
          titulo={`Detalle del registro n.° ${detalleModal.id}`}
          abierto={Boolean(detalleModal)}
          alCerrar={() => setDetalleModal(null)}
        >
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-3 rounded-lg border border-zinc-100 bg-zinc-50 p-3">
              <div>
                <span className="block text-xs font-medium text-zinc-400">Acción</span>
                <span className="font-semibold text-zinc-800">{textoAccion(detalleModal.accion)}</span>
              </div>
              <div>
                <span className="block text-xs font-medium text-zinc-400">Sección</span>
                <span className="font-semibold text-zinc-800">
                  {textoEntidad(detalleModal.entidad)}{" "}
                  {detalleModal.entidad_id ? `n.° ${detalleModal.entidad_id}` : ""}
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
              <DetalleValores titulo="Cómo estaba antes" valores={detalleModal.valor_anterior} />
            )}

            {detalleModal.valor_nuevo && (
              <DetalleValores titulo="Cómo quedó" valores={detalleModal.valor_nuevo} />
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
