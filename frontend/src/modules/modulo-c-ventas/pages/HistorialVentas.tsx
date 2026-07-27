// Página de historial de ventas con filtros. Anular y devolver los puede hacer
// también el cajero (HU-C08): no se pide autorización previa, pero TODO deja
// rastro que la administradora revisa desde su panel de caja y la bitácora.
// El backend valida los permisos (ventas.anular / ventas.devolver) en servidor.
import { useEffect, useState } from "react";
import { Ban, History, ListChecks, Printer, Undo2 } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  DatePicker,
  EmptyState,
  Input,
  Modal,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
  PaginacionControles,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useTema } from "../../../shared/lib/theme-context";
import { ModalDetalleVenta, type ModoGestion } from "../components/ModalDetalleVenta";
import { imprimirTicket, preferenciaPapel } from "../services/ticket-printer";
import { useVenta } from "../hooks/useVenta";
import type { Venta } from "../types";

export default function HistorialVentas() {
  const { tema } = useTema();
  const { ventas, paginados, cargando, error, noDisponible, recargar, registrar, anular, devolver } =
    useVenta();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  /** Rango efectivamente aplicado (el que viaja al backend). */
  const [rango, setRango] = useState<{ desde?: string; hasta?: string }>({});

  useEffect(() => {
    void recargar(rango.desde, rango.hasta, page, pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rango, page, pageSize]);

  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [paraAnular, setParaAnular] = useState<Venta | null>(null);
  /** Venta abierta en el modal de detalle/gestión (ver, devolver o cambiar). */
  const [paraGestionar, setParaGestionar] = useState<Venta | null>(null);
  const [modoGestion, setModoGestion] = useState<ModoGestion>("detalle");
  const [motivo, setMotivo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  /** Abre el modal de detalle en la pestaña indicada. */
  function abrirGestion(v: Venta, modo: ModoGestion) {
    setErrorAccion(null);
    setModoGestion(modo);
    setParaGestionar(v);
  }

  async function manejarAnular() {
    if (!paraAnular) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await anular(paraAnular.id, motivo);
      setMensaje(
        `Venta #${paraAnular.id} anulada: stock repuesto y caja ajustada. El rastro queda para la administradora.`
      );
      setParaAnular(null);
      setMotivo("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  async function manejarDevolver(items: { detalle_id: number; cantidad: number }[], motivoDev: string) {
    if (!paraGestionar) return;
    const id = paraGestionar.id;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await devolver(id, items, motivoDev);
      await recargar(rango.desde, rango.hasta, page, pageSize);
      setMensaje(`Devolución registrada en la venta #${id}: stock repuesto y rastro guardado.`);
      setParaGestionar(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  // Cambio de producto (HU-C08): se compone con las operaciones que ya existen.
  // Primero se devuelve lo original (repone stock, saca el dinero de la caja) y
  // luego se registra la venta nueva del reemplazo; la diferencia queda como el
  // neto entre ambos movimientos. Se devuelve primero a propósito: si el
  // reemplazo fallara (ej. sin stock), el cliente igual queda con su devolución
  // hecha en vez de cobrado de más.
  async function manejarCambiar(payload: {
    devolver: { detalle_id: number; cantidad: number }[];
    nuevos: { producto_id: number; cantidad: number }[];
    metodo: string;
    motivo: string;
  }) {
    if (!paraGestionar) return;
    const id = paraGestionar.id;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await devolver(id, payload.devolver, payload.motivo);
      try {
        const nueva = await registrar({ items: payload.nuevos, pagos: [{ metodo: payload.metodo }] });
        setMensaje(
          `Cambio en la venta #${id}: devolución registrada y venta nueva #${nueva.id} por ` +
            `S/ ${nueva.total.toFixed(2)} (${nueva.metodo_pago}). Todo queda para la administradora.`
        );
        setParaGestionar(null);
      } catch (e) {
        // La devolución sí quedó registrada; solo falló vender el reemplazo.
        setErrorAccion(
          `La devolución se registró, pero no se pudo vender el reemplazo: ${mensajeDeError(e)}. ` +
            `Regístralo aparte en el punto de venta.`
        );
      } finally {
        await recargar(rango.desde, rango.hasta, page, pageSize);
      }
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Historial de ventas" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas (Módulo C)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Venta>[] = [
    { titulo: "N°", ancho: "64px", render: (v) => <span className="font-mono text-xs text-zinc-500">#{v.id}</span> },
    {
      titulo: "Fecha",
      ancho: "108px",
      render: (v) => {
        if (!v.created_at) return <span className="text-zinc-400">—</span>;
        const f = new Date(v.created_at);
        return (
          <div className="leading-tight">
            <div className="text-zinc-700">{f.toLocaleDateString("es-PE")}</div>
            <div className="text-xs text-zinc-400">
              {f.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}
            </div>
          </div>
        );
      },
    },
    {
      // Los productos ya no se amontonan en la celda: un botón abre el detalle
      // completo en un modal (y desde ahí se devuelve o se cambia).
      titulo: "Items",
      ancho: "64px",
      alinear: "centro",
      render: (v) => (
        <Button
          variante="secundario"
          compacto
          title={`Ver ${v.items.length} producto(s)`}
          aria-label={`Ver productos de la venta ${v.id}`}
          onClick={() => abrirGestion(v, "detalle")}
          icono={<ListChecks className="h-4 w-4" aria-hidden />}
        >
          {v.items.length}
        </Button>
      ),
    },
    { titulo: "Vendedor", ancho: "130px", soloEscritorio: true, render: (v) => <span className="block truncate">{v.vendedor}</span> },
    { titulo: "Pago", ancho: "104px", render: (v) => <Badge tono="neutro">{v.metodo_pago}</Badge> },
    {
      titulo: "Total",
      ancho: "92px",
      alinear: "derecha",
      render: (v) => (
        <span className={`font-medium tabular-nums ${v.anulada ? "text-zinc-400 line-through" : "text-zinc-900"}`}>
          S/ {v.total.toFixed(2)}
        </span>
      ),
    },
    {
      titulo: "Estado",
      ancho: "104px",
      render: (v) =>
        v.estado === "ANULADA" ? (
          <Badge tono="peligro">Anulada</Badge>
        ) : v.estado === "DEVUELTA_PARCIAL" ? (
          <Badge tono="alerta">Dev. parcial</Badge>
        ) : (
          <Badge tono="exito">Válida</Badge>
        ),
    },
    {
      // HU-C05: reimprimir el ticket si el cliente lo pide después
      titulo: "Ticket",
      ancho: "60px",
      alinear: "centro",
      render: (v) =>
        v.anulada ? null : (
          <Button
            variante="fantasma"
            compacto
            title="Imprimir ticket"
            aria-label={`Imprimir ticket de la venta ${v.id}`}
            onClick={() =>
              imprimirTicket(
                v,
                { nombre: tema.nombreNegocio, logoUrl: tema.logoUrl },
                preferenciaPapel.obtener()
              )
            }
            icono={<Printer className="h-4 w-4" aria-hidden />}
          />
        ),
    },
    {
      titulo: "Acciones",
      ancho: "150px",
      render: (v: Venta) =>
        v.anulada ? (
          <span className="text-xs text-zinc-400">—</span>
        ) : (
          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              variante="secundario"
              compacto
              className="w-28 justify-center"
              onClick={() => abrirGestion(v, "devolver")}
              icono={<Undo2 className="h-4 w-4" aria-hidden />}
            >
              Devolver
            </Button>
            <Button
              variante="secundario"
              compacto
              className="w-28 justify-center text-peligro"
              onClick={() => {
                setErrorAccion(null);
                setParaAnular(v);
              }}
              icono={<Ban className="h-4 w-4" aria-hidden />}
            >
              Anular
            </Button>
          </div>
        ),
    },
  ];

  return (
    <div>
      <PageHeader titulo="Historial de ventas" descripcion="Todas las ventas registradas en el POS." />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-2">
          <span className="mb-2 mr-1 hidden text-sm font-medium text-zinc-500 sm:inline">Rango:</span>
          <div className="w-36">
            <DatePicker label="Desde" mostrarAnio valor={desde} alCambiar={(f) => setDesde(f)} />
          </div>
          <div className="w-36">
            <DatePicker label="Hasta" mostrarAnio valor={hasta} alCambiar={(f) => setHasta(f)} />
          </div>
          <Button
            variante="secundario"
            compacto
            onClick={() => {
              setPage(1);
              setRango({ desde: desde || undefined, hasta: hasta || undefined });
            }}
          >
            Filtrar
          </Button>
          {(desde || hasta || rango.desde || rango.hasta) && (
            <Button
              variante="fantasma"
              compacto
              onClick={() => {
                setDesde("");
                setHasta("");
                setPage(1);
                setRango({});
              }}
            >
              Limpiar
            </Button>
          )}
        </div>
      </Card>

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}
      {cargando && <PageSpinner texto="Cargando ventas…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            minAncho="100%"
            columnas={columnas}
            filas={ventas}
            claveDe={(v) => v.id}
            vacio={
              <EmptyState
                icono={History}
                titulo="Sin ventas"
                descripcion="Aún no hay ventas en el período elegido."
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={(n) => {
              setPageSize(n);
              setPage(1);
            }}
            etiqueta="ventas"
          />
        </Card>
      )}

      <Modal
        abierto={paraAnular !== null}
        titulo={`Anular venta #${paraAnular?.id}`}
        alCerrar={() => setParaAnular(null)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setParaAnular(null)}>
              Cancelar
            </Button>
            <Button variante="peligro" cargando={procesando} onClick={() => void manejarAnular()}>
              Anular venta
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-zinc-600">
            La anulación repone el stock, descuenta el efectivo de la caja actual y queda
            registrada con tu usuario para que la administradora la revise.
          </p>
          <Input
            label="Motivo"
            requerido
            placeholder="ej. cobro duplicado"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
        </div>
      </Modal>

      {/* Detalle de la venta: ver productos, devolver o cambiar por otro (HU-C08) */}
      <ModalDetalleVenta
        venta={paraGestionar}
        modoInicial={modoGestion}
        procesando={procesando}
        error={errorAccion}
        alCerrar={() => setParaGestionar(null)}
        alDevolver={(items, motivoDev) => void manejarDevolver(items, motivoDev)}
        alCambiar={(payload) => void manejarCambiar(payload)}
      />
    </div>
  );
}
