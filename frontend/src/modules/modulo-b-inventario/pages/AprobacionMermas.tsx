// Aprobación de Mermas: cola admin-only de mermas en estado "Registrada".
// Flujo de 2 pasos: confirmar (descuenta stock) o rechazar (no toca stock).
import { useEffect, useState } from "react";
import { Check, PackageX, X } from "lucide-react";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { useAuth } from "../../modulo-a-seguridad/hooks/useAuth";
import { codigoDeError, mensajeDeError } from "../../../shared/lib/http-client";
import { FormularioMermaEditable } from "../components/FormularioMermaEditable";
import { MermaDetalleContent } from "../components/MermaDetalleContent";
import { ModalConfirmacion } from "../components/ModalConfirmacion";
import { PaginacionControles } from "../components/PaginacionControles";
import { mapErrorCodeToMessage } from "../lib/mapErrorCodeToMessage";
import { useMermas } from "../hooks/useMermas";
import { useProductos } from "../hooks/useProductos";
import type { Merma, MermaUpdateBody } from "../types";

type ModoModal = "ver" | "editar" | null;

const MOTIVO_LABELS: Record<string, string> = {
  vencimiento: "Vencimiento",
  rotura: "Rotura",
  otro: "Otro",
};

export default function AprobacionMermas() {
  const { mermas, paginados, cargando, error, noDisponible, recargar, confirmar, rechazar, editar, obtener } =
    useMermas();
  const { productos } = useProductos({ page_size: 200 });
  const { usuario } = useAuth();

  const [detalle, setDetalle] = useState<Merma | null>(null);
  const [modo, setModo] = useState<ModoModal>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorDetalle, setErrorDetalle] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [errorEdicion, setErrorEdicion] = useState<string | null>(null);
  const [paraConfirmar, setParaConfirmar] = useState<Merma | null>(null);
  const [paraRechazar, setParaRechazar] = useState<Merma | null>(null);
  const [motivo, setMotivo] = useState("");
  const [procesando, setProcesando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    // Cola server-side: solo mermas en estado "Registrada".
    void recargar({ estado: "Registrada", page, page_size: pageSize });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  function nombreProducto(id: number): string {
    return productos.find((p) => p.id === id)?.nombre ?? `#${id}`;
  }

  async function abrirDetalle(m: Merma) {
    setModo("ver");
    setDetalle(m);
    setErrorDetalle(null);
    setCargandoDetalle(true);
    try {
      const fresca = await obtener(m.id);
      setDetalle(fresca);
    } catch (e) {
      setErrorDetalle(mensajeDeError(e));
    } finally {
      setCargandoDetalle(false);
    }
  }

  function cerrarDetalle() {
    setModo(null);
    setDetalle(null);
    setErrorEdicion(null);
  }

  async function manejarEditar(body: MermaUpdateBody) {
    if (!detalle) return;
    setEditando(true);
    setErrorEdicion(null);
    try {
      const actualizada = await editar(detalle.id, body);
      setDetalle(actualizada);
      setModo("ver");
    } catch (e) {
      const code = codigoDeError(e);
      setErrorEdicion(code ? mapErrorCodeToMessage(code) : mensajeDeError(e));
    } finally {
      setEditando(false);
    }
  }

  async function manejarConfirmar() {
    if (!paraConfirmar) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      const resp = await confirmar(paraConfirmar.id);
      setMensaje(
        `Merma #${paraConfirmar.id} confirmada${resp.stock_actualizado != null ? `: stock = ${resp.stock_actualizado}` : ""}.`,
      );
      setParaConfirmar(null);
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : "No se pudo confirmar.");
    } finally {
      setProcesando(false);
    }
  }

  async function manejarRechazar() {
    if (!paraRechazar) return;
    if (motivo.trim().length < 5) {
      setErrorAccion("El motivo debe tener al menos 5 caracteres.");
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      await rechazar(paraRechazar.id, { motivo_rechazo: motivo.trim() });
      setMensaje(`Merma #${paraRechazar.id} rechazada.`);
      setParaRechazar(null);
      setMotivo("");
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : "No se pudo rechazar.");
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Aprobación de mermas" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Merma>[] = [
    {
      titulo: "Fecha",
      render: (m) => (
        <span className="whitespace-nowrap text-zinc-500">
          {m.created_at ? new Date(m.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    { titulo: "Producto", render: (m) => nombreProducto(m.producto_id) },
    {
      titulo: "Cantidad",
      alinear: "derecha",
      render: (m) => <span className="tabular-nums">{m.cantidad}</span>,
    },
    {
      titulo: "Motivo",
      soloEscritorio: true,
      render: (m) => MOTIVO_LABELS[String(m.motivo)] ?? m.motivo,
    },
    {
      titulo: "Observación",
      soloEscritorio: true,
      render: (m) =>
        m.observacion ? (
          <span className="line-clamp-2 max-w-xs text-xs text-zinc-600">{m.observacion}</span>
        ) : (
          "—"
        ),
    },
    { titulo: "Reportó", soloEscritorio: true, render: (m) => m.registrado_por_nombre },
    {
      titulo: "Acciones",
      render: (m) => (
        <div className="flex gap-1">
          <Button compacto variante="secundario" onClick={() => void abrirDetalle(m)}>
            Ver detalle
          </Button>
          <Button
            compacto
            onClick={() => setParaConfirmar(m)}
            icono={<Check className="h-4 w-4" aria-hidden />}
          >
            Confirmar
          </Button>
          <Button
            compacto
            variante="secundario"
            className="text-peligro"
            onClick={() => {
              setParaRechazar(m);
              setMotivo("");
              setErrorAccion(null);
            }}
            icono={<X className="h-4 w-4" aria-hidden />}
          >
            Rechazar
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Aprobación de mermas"
        descripcion="Cola de mermas reportadas. Confirmar descuenta stock; rechazar la deja sin efecto."
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}
      {errorAccion && (
        <div className="mb-4">
          <Alert tono="peligro">{errorAccion}</Alert>
        </div>
      )}

      {cargando && mermas.length === 0 ? (
        <PageSpinner texto="Cargando cola…" />
      ) : error ? (
        <Alert tono="peligro">{error}</Alert>
      ) : (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={mermas}
            claveDe={(m) => m.id}
            vacio={
              <EmptyState
                icono={PackageX}
                titulo="Cola vacía"
                descripcion="No hay mermas pendientes de aprobación."
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={setPageSize}
            etiqueta="pendientes"
          />
        </Card>
      )}

      {/* Modal: detalle / edición (sdd/modulo-b-aprobaciones-detalle-editar) */}
      {detalle && modo && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-900/40 p-0 sm:items-center sm:p-4"
          onClick={cerrarDetalle}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={modo === "editar" ? "Editar merma" : "Detalle de la merma"}
            className="max-h-[90vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-lg sm:max-w-lg sm:rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
              <h3 className="font-semibold text-zinc-900">
                Merma #{detalle.id}{" "}
                {modo === "editar" && (
                  <span className="text-sm font-normal text-zinc-500">(editando)</span>
                )}
              </h3>
              <button
                onClick={cerrarDetalle}
                aria-label="Cerrar"
                className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
              >
                <X className="h-5 w-5" />
              </button>
            </header>
            <div className="space-y-4 px-5 py-4">
              {cargandoDetalle && modo === "ver" ? (
                <PageSpinner texto="Cargando detalle…" />
              ) : errorDetalle && modo === "ver" ? (
                <Alert tono="peligro">{errorDetalle}</Alert>
              ) : modo === "ver" ? (
                <MermaDetalleContent
                  merma={detalle}
                  currentUser={usuario}
                  productos={productos}
                  onEditarClick={() => setModo("editar")}
                />
              ) : (
                <FormularioMermaEditable
                  inicial={detalle}
                  onSubmit={manejarEditar}
                  onCancel={() => setModo("ver")}
                  procesando={editando}
                  error={errorEdicion}
                />
              )}
            </div>
            {modo === "ver" && (
              <footer className="flex justify-end gap-2 border-t border-zinc-100 px-5 py-4">
                <Button variante="secundario" onClick={cerrarDetalle}>
                  Cerrar
                </Button>
                <Button
                  onClick={() => {
                    setParaConfirmar(detalle);
                    cerrarDetalle();
                  }}
                  icono={<Check className="h-4 w-4" aria-hidden />}
                >
                  Confirmar
                </Button>
                <Button
                  variante="secundario"
                  className="text-peligro"
                  onClick={() => {
                    setParaRechazar(detalle);
                    setMotivo("");
                    cerrarDetalle();
                  }}
                  icono={<X className="h-4 w-4" aria-hidden />}
                >
                  Rechazar
                </Button>
              </footer>
            )}
          </div>
        </div>
      )}

      <ModalConfirmacion
        abierto={paraConfirmar !== null}
        titulo="Confirmar merma"
        mensaje={
          paraConfirmar
            ? `Vas a descontar ${paraConfirmar.cantidad} unidades de "${nombreProducto(
                paraConfirmar.producto_id,
              )}" del stock. Esta acción no se puede deshacer.`
            : ""
        }
        textoConfirmar="Confirmar"
        cargando={procesando}
        alCancelar={() => setParaConfirmar(null)}
        alConfirmar={() => void manejarConfirmar()}
      />

      {/* Modal de rechazo (con motivo obligatorio ≥5 chars) */}
      <div
        className={`fixed inset-0 z-50 flex items-end justify-center bg-zinc-900/40 p-0 sm:items-center sm:p-4 ${
          paraRechazar ? "" : "hidden"
        }`}
        onClick={() => !procesando && setParaRechazar(null)}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Rechazar merma"
          className="w-full max-w-lg overflow-hidden rounded-t-2xl bg-white shadow-lg sm:rounded-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
            <h3 className="font-semibold text-zinc-900">Rechazar merma #{paraRechazar?.id}</h3>
            <button
              onClick={() => setParaRechazar(null)}
              disabled={procesando}
              aria-label="Cerrar"
              className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 disabled:opacity-50"
            >
              <X className="h-5 w-5" />
            </button>
          </header>
          <div className="space-y-3 px-5 py-4">
            {paraRechazar && (
              <p className="text-sm text-zinc-600">
                Vas a rechazar la merma de{" "}
                <strong>{paraRechazar.cantidad}</strong> unidades de{" "}
                <strong>{nombreProducto(paraRechazar.producto_id)}</strong>.
              </p>
            )}
            <Input
              label="Motivo del rechazo"
              requerido
              placeholder="ej. el producto aún está vigente, no corresponde merma"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
            {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
          </div>
          <footer className="flex justify-end gap-2 border-t border-zinc-100 px-5 py-4">
            <Button variante="secundario" onClick={() => setParaRechazar(null)} disabled={procesando}>
              Cancelar
            </Button>
            <Button variante="peligro" cargando={procesando} onClick={() => void manejarRechazar()}>
              Rechazar merma
            </Button>
          </footer>
        </div>
      </div>
    </div>
  );
}
