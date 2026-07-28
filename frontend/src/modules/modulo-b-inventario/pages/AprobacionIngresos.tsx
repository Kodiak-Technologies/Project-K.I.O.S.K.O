// Página para aprobar o rechazar ingresos de mercadería pendientes (solo ADMIN).
//
// La cola de solicitudes es una tabla de filas. El detalle se abre en un pop-up
// dividido en dos: a la izquierda los productos por ingresar (cantidad y costo
// unitario) y a la derecha la boleta, para contrastarlos sin perder de vista
// ninguno de los dos.
import { useEffect, useState } from "react";
import { Check, ClipboardCheck, Eye, ImageOff, X } from "lucide-react";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  ImagenConRespaldo,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { useAuth } from "../../modulo-a-seguridad/hooks/useAuth";
import { codigoDeError, mensajeDeError, urlParaAbrir } from "../../../shared/lib/http-client";
import { FormularioIngresoEditable } from "../components/FormularioIngresoEditable";
import { IngresoDetalleContent } from "../components/IngresoDetalleContent";
import { ModalConfirmacion } from "../components/ModalConfirmacion";
import { usePaginacionCursor } from "../../../shared/lib/use-paginacion-cursor";
import { PaginacionControles } from "../components/PaginacionControles";
import { mapErrorCodeToMessage } from "../lib/mapErrorCodeToMessage";
import { useIngresos } from "../hooks/useIngresos";
import type { SolicitudIngreso, SolicitudIngresoUpdateBody } from "../types";

type ModoPanel = "ver" | "editar" | null;

export default function AprobacionIngresos() {
  // Filtro server-side: solo pendientes (la cola de aprobación).
  const { ingresos, paginados, cargando, error, noDisponible, recargar, aprobar, rechazar, editar, obtener } =
    useIngresos();
  const { usuario } = useAuth();

  const [detalle, setDetalle] = useState<SolicitudIngreso | null>(null);
  const [modo, setModo] = useState<ModoPanel>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorDetalle, setErrorDetalle] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [errorEdicion, setErrorEdicion] = useState<string | null>(null);
  const [paraAprobar, setParaAprobar] = useState<SolicitudIngreso | null>(null);
  const [paraRechazar, setParaRechazar] = useState<SolicitudIngreso | null>(null);
  const [motivo, setMotivo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  // La cola crece mientras la administradora la revisa: con `page`/OFFSET
  // cada ingreso nuevo le corría las filas y le repetía solicitudes.
  const paginacion = usePaginacionCursor(20);
  const { page, pageSize, cursor, registrarRespuesta } = paginacion;

  useEffect(() => {
    void recargar({
      estado: "Pendiente",
      page_size: pageSize,
      ...(cursor ? { cursor } : {}),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, cursor]);

  useEffect(() => {
    if (paginados) registrarRespuesta(paginados.siguiente_cursor);
  }, [paginados, registrarRespuesta]);

  async function abrirDetalle(s: SolicitudIngreso) {
    setModo("ver");
    setDetalle(s);
    setErrorDetalle(null);
    setCargandoDetalle(true);
    try {
      const fresca = await obtener(s.id);
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

  async function manejarEditar(body: SolicitudIngresoUpdateBody) {
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

  async function manejarAprobar() {
    if (!paraAprobar) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      const resp = await aprobar(paraAprobar.id);
      setMensaje(
        `Ingreso #${paraAprobar.id} aprobado: +${resp.unidades_agregadas} unidades en ${resp.productos_actualizados} producto(s).`,
      );
      setParaAprobar(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
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
      setMensaje(`Ingreso #${paraRechazar.id} rechazado.`);
      setParaRechazar(null);
      setMotivo("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Aprobación de ingresos" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario" />
        </Card>
      </div>
    );
  }
  if (cargando && ingresos.length === 0) return <PageSpinner texto="Cargando pendientes…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const columnas: Columna<SolicitudIngreso>[] = [
    {
      titulo: "Fecha",
      render: (i) => (
        <span className="whitespace-nowrap text-zinc-500">
          {i.created_at ? new Date(i.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Foto boleta",
      render: (i) =>
        i.foto_boleta_url ? (
          <a href={urlParaAbrir(i.foto_boleta_url)} target="_blank" rel="noopener noreferrer" className="block">
            <ImagenConRespaldo
              src={i.foto_boleta_url}
              alt="Boleta"
              className="h-10 w-10 rounded border border-zinc-200 object-cover hover:opacity-80"
              respaldo={
                <span className="flex h-10 w-10 items-center justify-center rounded border border-dashed border-zinc-300 text-zinc-300">
                  <ImageOff className="h-4 w-4" aria-hidden />
                </span>
              }
            />
          </a>
        ) : (
          <span className="text-xs text-zinc-400">Sin foto</span>
        ),
    },
    {
      titulo: "Productos",
      render: (i) => (
        <div>
          <span className="font-medium text-zinc-800">
            {i.cantidad_productos ?? i.lineas.length} unidades
          </span>
          <p className="text-xs text-zinc-500">{i.lineas.length} línea(s)</p>
        </div>
      ),
    },
    {
      titulo: "Solicitado por",
      soloEscritorio: true,
      render: (i) => i.solicitado_por_nombre,
    },
    {
      titulo: "Acciones",
      alinear: "derecha",
      ancho: "220px",
      render: (i) => (
        <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
          <Button
            compacto
            variante="secundario"
            title="Ver detalle"
            aria-label={`Ver detalle de la solicitud ${i.id}`}
            onClick={() => void abrirDetalle(i)}
            icono={<Eye className="h-4 w-4" aria-hidden />}
          />
          <Button
            compacto
            onClick={() => setParaAprobar(i)}
            icono={<Check className="h-4 w-4" aria-hidden />}
          >
            Aprobar
          </Button>
          <Button
            compacto
            variante="secundario"
            className="text-peligro"
            onClick={() => {
              setParaRechazar(i);
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
        titulo="Aprobación de ingresos"
        descripcion="Solo lo aprobado suma al stock. Cada decisión queda en la bitácora."
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

      {/* La cola sigue siendo una tabla de filas, a todo el ancho. */}
      <Card sinPadding>
        <Table
          columnas={columnas}
          filas={ingresos}
          claveDe={(i) => i.id}
          alHacerClicFila={(i) => void abrirDetalle(i)}
          vacio={
            <EmptyState
              icono={ClipboardCheck}
              titulo="Nada pendiente"
              descripcion="No hay ingresos esperando aprobación."
            />
          }
        />
        <PaginacionControles
          paginados={paginados}
          page={page}
          pageSize={pageSize}
          onCambiarPage={paginacion.onCambiarPage}
          onCambiarPageSize={paginacion.onCambiarPageSize}
          etiqueta="pendientes"
        />
      </Card>

      {/* Detalle en pop-up: a la IZQUIERDA los productos por ingresar
          (cantidad y costo unitario), a la DERECHA la boleta para contrastar. */}
      {detalle && modo && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-900/40 p-0 sm:items-center sm:p-4"
          onClick={cerrarDetalle}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={modo === "editar" ? "Editar solicitud" : "Detalle de la solicitud"}
            className="flex max-h-[92vh] w-full flex-col overflow-hidden rounded-t-2xl bg-white shadow-lg sm:max-w-5xl sm:rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
              <h3 className="font-semibold text-zinc-900">
                Solicitud #{detalle.id}
                {modo === "editar" && (
                  <span className="ml-1 text-sm font-normal text-zinc-500">(editando)</span>
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

            <div className="grid flex-1 gap-5 overflow-y-auto px-5 py-4 lg:grid-cols-[1fr_22rem] lg:items-start">
              {/* Izquierda: qué se está por ingresar */}
              <div>
                {cargandoDetalle && modo === "ver" ? (
                  <PageSpinner texto="Cargando detalle…" />
                ) : errorDetalle && modo === "ver" ? (
                  <Alert tono="peligro">{errorDetalle}</Alert>
                ) : modo === "ver" ? (
                  <IngresoDetalleContent
                    ingreso={detalle}
                    currentUser={usuario}
                    onEditarClick={() => setModo("editar")}
                  />
                ) : (
                  <FormularioIngresoEditable
                    inicial={detalle}
                    onSubmit={manejarEditar}
                    onCancel={() => setModo("ver")}
                    procesando={editando}
                    error={errorEdicion}
                  />
                )}
              </div>

              {/* Derecha: la boleta (fija al scrollear la tabla) */}
              <div className="lg:sticky lg:top-0 h-fit">
                <h4 className="mb-2 text-sm font-semibold text-zinc-800">Boleta</h4>
                {detalle.foto_boleta_url ? (
                  <a
                    href={urlParaAbrir(detalle.foto_boleta_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Abrir la boleta en tamaño completo"
                    className="block rounded-lg border border-zinc-200 bg-zinc-50 p-2"
                  >
                    <ImagenConRespaldo
                      src={detalle.foto_boleta_url}
                      alt={`Boleta de la solicitud #${detalle.id}`}
                      className="max-h-[28rem] w-full rounded object-contain"
                      respaldo={
                        <span className="flex items-center gap-2 px-3 py-6 text-sm text-zinc-500">
                          <ImageOff className="h-4 w-4" aria-hidden />
                          No se pudo cargar la boleta. Ábrela en una pestaña nueva para verla.
                        </span>
                      }
                    />
                  </a>
                ) : (
                  <p className="flex items-center gap-2 rounded-lg border border-dashed border-zinc-300 px-3 py-6 text-sm text-zinc-500">
                    <ImageOff className="h-4 w-4" aria-hidden />
                    Esta solicitud no tiene boleta adjunta.
                  </p>
                )}
              </div>
            </div>

            {modo === "ver" && (
              <footer className="flex flex-wrap justify-end gap-2 border-t border-zinc-100 px-5 py-4">
                <Button variante="secundario" onClick={cerrarDetalle}>
                  Cerrar
                </Button>
                <Button
                  onClick={() => {
                    setParaAprobar(detalle);
                    cerrarDetalle();
                  }}
                  icono={<Check className="h-4 w-4" aria-hidden />}
                >
                  Aprobar
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

      {/* Modal: confirmar aprobación */}
      <ModalConfirmacion
        abierto={paraAprobar !== null}
        titulo="Aprobar ingreso"
        mensaje={
          paraAprobar
            ? `Vas a sumar ${paraAprobar.cantidad_productos ?? paraAprobar.lineas.length} unidades al stock de ${
                paraAprobar.lineas.length
              } producto(s). Esta acción no se puede deshacer.`
            : ""
        }
        textoConfirmar="Aprobar"
        cargando={procesando}
        alCancelar={() => setParaAprobar(null)}
        alConfirmar={() => void manejarAprobar()}
      />

      {/* Modal: rechazar (con motivo obligatorio) */}
      <div
        className={`fixed inset-0 z-50 flex items-end justify-center bg-zinc-900/40 p-0 sm:items-center sm:p-4 ${
          paraRechazar ? "" : "hidden"
        }`}
        onClick={() => !procesando && setParaRechazar(null)}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Rechazar ingreso"
          className="w-full max-w-lg overflow-hidden rounded-t-2xl bg-white shadow-lg sm:rounded-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
            <h3 className="font-semibold text-zinc-900">Rechazar ingreso #{paraRechazar?.id}</h3>
            <button
              onClick={() => setParaRechazar(null)}
              disabled={procesando}
              aria-label="Cerrar"
              className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 disabled:opacity-50"
            >
              <X className="h-5 w-5" />
            </button>
          </header>
          <div className="px-5 py-4">
            <Input
              label="Motivo del rechazo"
              requerido
              placeholder="ej. cantidad no coincide con la guía"
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
              Rechazar ingreso
            </Button>
          </footer>
        </div>
      </div>
    </div>
  );
}
