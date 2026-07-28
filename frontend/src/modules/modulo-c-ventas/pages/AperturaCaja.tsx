// Página de caja ("/caja"): muestra el turno actual, permite abrirlo si está
// cerrada y enlaza al cierre. A la derecha, el historial de aperturas y cierres,
// visible para TODOS los usuarios: en un cambio de turno el cajero entrante ve
// con cuánto abrió y cerró el anterior; la administradora supervisa lo mismo.
import { useState, useEffect, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Eye, History, Wallet, MessageSquare, UserPlus } from "lucide-react";
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
} from "../../../shared/components/ui";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { ModalRastroTurno } from "../components/ModalRastroTurno";
import { useCaja } from "../hooks/useCaja";
import type { TurnoCaja } from "../types";
import { usuariosHttpAdapter } from "../../modulo-a-seguridad/services/usuarios.http-adapter";
import type { Usuario } from "../../modulo-a-seguridad/types";

/** Formatea una fecha ISO como "HH:MM a. m./p. m." (solo hora). */
function soloHora(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("es-PE", { timeStyle: "short" });
}

/** Devuelve la fecha local en formato YYYY-MM-DD para usar como value del input[type=date]. */
function hoyISO(): string {
  const hoy = new Date();
  const y = hoy.getFullYear();
  const m = String(hoy.getMonth() + 1).padStart(2, "0");
  const d = String(hoy.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Extrae la parte de fecha local (YYYY-MM-DD) de una cadena ISO. */
function fechaLocalDe(iso: string): string {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dia}`;
}

export default function AperturaCaja() {
  const { usuario } = useAuthContext();
  const { turno, turnos, cargando, error, noDisponible, abrir, editar } = useCaja();
  const [montoInicial, setMontoInicial] = useState("");
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  // HU-C08: modal con el rastro del turno (ventas, anulaciones, devoluciones)
  const [turnoRastro, setTurnoRastro] = useState<TurnoCaja | null>(null);
  // Filtro de fecha para el historial (por defecto: hoy)
  const [fechaFiltro, setFechaFiltro] = useState<string>(hoyISO);
  // Modal para ver comentarios largos
  const [comentarioModal, setComentarioModal] = useState<string | null>(null);
  const esAdmin = usuario?.rol === "ADMIN";

  const [modalAsignar, setModalAsignar] = useState(false);
  const [cajeros, setCajeros] = useState<Usuario[]>([]);
  const [cargandoCajeros, setCargandoCajeros] = useState(false);
  const [errorAsignar, setErrorAsignar] = useState<string | null>(null);
  const [cajeroSeleccionado, setCajeroSeleccionado] = useState<number | null>(null);
  const [montoInicialEdicion, setMontoInicialEdicion] = useState("");
  const [asignando, setAsignando] = useState(false);

  useEffect(() => {
    let montado = true;
    if (esAdmin && cajeros.length === 0) {
      usuariosHttpAdapter.listar().then(lista => {
        if (montado) setCajeros(lista.filter(u => u.activo));
      });
    }
    return () => { montado = false; };
  }, [esAdmin, cajeros.length]);

  const turnoAsignadoAOtro = 
    turno && turno.asignado_a_id !== null && turno.asignado_a_id !== usuario?.id && !esAdmin;

  async function manejarAbrir(evento: FormEvent) {
    evento.preventDefault();
    const monto = Number(montoInicial);
    if (Number.isNaN(monto) || monto < 0) {
      setErrorAccion("Ingresa el efectivo inicial (0 o más).");
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      await abrir(monto);
      setMontoInicial("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  async function abrirModalAsignar() {
    setModalAsignar(true);
    setErrorAsignar(null);
    setCajeroSeleccionado(turno?.asignado_a_id ?? null);
    setMontoInicialEdicion(turno ? turno.monto_inicial.toString() : "");
    if (cajeros.length === 0) {
      setCargandoCajeros(true);
      try {
        const lista = await usuariosHttpAdapter.listar();
        setCajeros(lista.filter((u) => u.activo));
      } catch (e) {
        setErrorAsignar(mensajeDeError(e));
      } finally {
        setCargandoCajeros(false);
      }
    }
  }

  async function asignarCajero() {
    setAsignando(true);
    setErrorAsignar(null);
    try {
      const montoParsed = Number(montoInicialEdicion);
      if (Number.isNaN(montoParsed) || montoParsed < 0) {
        throw new Error("El monto inicial debe ser 0 o mayor.");
      }
      await editar(turno!.id, { asignado_a_id: cajeroSeleccionado, monto_inicial: montoParsed });
      setModalAsignar(false);
    } catch(e) {
      setErrorAsignar(mensajeDeError(e));
    } finally {
      setAsignando(false);
    }
  }

  const usuarioAsignado = cajeros.find(c => c.id === turno?.asignado_a_id);

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Caja" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Consultando la caja…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const abierta = turno?.estado === "ABIERTO";

  // Filtrar turnos por la fecha seleccionada (comparando fecha local de apertura)
  const turnosFiltrados = turnos.filter((t) => fechaLocalDe(t.abierto_en) === fechaFiltro);

  const columnas: Columna<TurnoCaja>[] = [
    { titulo: "N°", alinear: "centro", render: (t) => <span className="font-mono text-xs text-zinc-500">#{t.id}</span> },
    {
      titulo: "Abierta por",
      alinear: "centro",
      render: (t) => (
        <span className="block max-w-[8rem] truncate font-medium text-zinc-800 mx-auto" title={t.abierto_por}>
          {t.abierto_por}
        </span>
      ),
    },
    {
      // Solo muestra la hora porque el día ya está seleccionado en el filtro
      titulo: "Apertura",
      alinear: "centro",
      render: (t) => <span className="whitespace-nowrap text-zinc-500">{soloHora(t.abierto_en)}</span>,
    },
    {
      titulo: "Monto inicial",
      alinear: "centro",
      render: (t) => <span className="tabular-nums whitespace-nowrap">S/ {t.monto_inicial.toFixed(2)}</span>,
    },
    {
      // Solo muestra la hora porque el día ya está seleccionado en el filtro
      titulo: "Cierre",
      soloEscritorio: true,
      alinear: "centro",
      render: (t) => <span className="whitespace-nowrap text-zinc-500">{soloHora(t.cerrado_en)}</span>,
    },
    {
      titulo: "Contado al cierre",
      alinear: "centro",
      render: (t) => (
        <span className="tabular-nums whitespace-nowrap">
          {t.monto_final !== null ? `S/ ${t.monto_final.toFixed(2)}` : "—"}
        </span>
      ),
    },
    {
      titulo: "Cerrada por",
      soloEscritorio: true,
      alinear: "centro",
      render: (t) => (
        <span className="block max-w-[8rem] truncate text-zinc-700 mx-auto" title={t.cerrado_por ?? undefined}>
          {t.cerrado_por ?? "—"}
        </span>
      ),
    },
    {
      // HU-C07: el descuadre (y su comentario) a la vista de la administradora
      titulo: "Diferencia",
      alinear: "centro",
      render: (t) => {
        if (!t.arqueo) return <span className="text-zinc-400">—</span>;
        if (t.arqueo.diferencia === 0) return <Badge tono="exito">Cuadró</Badge>;
        return (
          <span title={t.arqueo.comentario ?? undefined} className="inline-flex items-center gap-1 whitespace-nowrap">
            <Badge tono="alerta">
              {t.arqueo.diferencia > 0 ? "+" : ""}S/ {t.arqueo.diferencia.toFixed(2)}
            </Badge>
          </span>
        );
      },
    },
    {
      titulo: "Comentario",
      soloEscritorio: true,
      alinear: "centro",
      render: (t) =>
        t.arqueo?.comentario ? (
          <Button
            variante="fantasma"
            compacto
            aria-label="Ver comentario"
            onClick={() => setComentarioModal(t.arqueo!.comentario!)}
            icono={<MessageSquare className="h-4 w-4 text-zinc-500" aria-hidden />}
          />
        ) : (
          <span className="text-zinc-400">—</span>
        ),
    },
    {
      titulo: "Estado",
      alinear: "centro",
      render: (t) => {
        if (t.estado === "ABIERTO") {
          return <div className="h-3 w-3 rounded-full bg-exito-intenso mx-auto cursor-help" title="Abierto" />;
        }
        if (t.cerrado_por === "Sistema") {
          return <div className="h-3 w-3 rounded-full bg-alerta-intenso mx-auto cursor-help" title="Cerrado por el Sistema" />;
        }
        return <div className="h-3 w-3 rounded-full bg-zinc-400 mx-auto cursor-help" title="Cerrado" />;
      },
    },
    // HU-C08: la administradora abre el rastro completo del turno en un modal
    ...(esAdmin
      ? [
          {
            titulo: "Movimientos",
            alinear: "centro",
            render: (t: TurnoCaja) => (
              <Button
                variante="fantasma"
                compacto
                aria-label={`Ver movimientos del turno ${t.id}`}
                onClick={() => setTurnoRastro(t)}
                icono={<Eye className="h-4 w-4" aria-hidden />}
              >
                Ver
              </Button>
            ),
          } satisfies Columna<TurnoCaja>,
        ]
      : []),
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        titulo="Caja"
        descripcion="Abre un turno al empezar el día y ciérralo al terminar. Todos ven las aperturas y cierres."
        acciones={<Badge tono={abierta ? "exito" : "neutro"}>{abierta ? "Abierta" : "Cerrada"}</Badge>}
      />

      {/* Fila superior: tarjeta de turno en curso / apertura */}
      <div>
        {abierta && turno ? (
          <Card titulo="Turno en curso">
            {/* Datos del turno: centrados horizontalmente con separadores */}
            <dl className="flex flex-wrap items-center justify-center gap-0 divide-x divide-zinc-200 text-sm">
              <div className="flex flex-col items-center px-8 py-2">
                <dt className="text-xs uppercase tracking-wide text-zinc-400">Abierta por</dt>
                <dd className="mt-1 font-semibold text-zinc-800">{turno.abierto_por}</dd>
              </div>
              <div className="flex flex-col items-center px-8 py-2">
                <dt className="text-xs uppercase tracking-wide text-zinc-400">Desde</dt>
                <dd className="mt-1 font-semibold text-zinc-800">{soloHora(turno.abierto_en)}</dd>
              </div>
              <div className="flex flex-col items-center px-8 py-2">
                <dt className="text-xs uppercase tracking-wide text-zinc-400">Efectivo inicial</dt>
                <dd className="mt-1 font-semibold tabular-nums text-zinc-800">S/ {turno.monto_inicial.toFixed(2)}</dd>
              </div>
              {usuarioAsignado && (
                <div className="flex flex-col items-center px-8 py-2">
                  <dt className="text-xs uppercase tracking-wide text-zinc-400">Asignada a</dt>
                  <dd className="mt-1 font-semibold text-zinc-800">{usuarioAsignado.nombre}</dd>
                </div>
              )}
            </dl>
            {/* Botones centrados, mismo tamaño, moderados */}
            <div className="mt-5 flex justify-center gap-3">
              {turnoAsignadoAOtro ? (
                <Alert tono="alerta">Este turno ha sido asignado a otro cajero. No puedes operar en él.</Alert>
              ) : (
                <>
                  <Link to="/pos" className="w-44">
                    <Button className="w-full">Ir a vender</Button>
                  </Link>
                  <Link to="/caja/cierre" className="w-44">
                    <Button variante="secundario" className="w-full">Ir al cierre de caja</Button>
                  </Link>
                  {esAdmin && (
                    <Button variante="fantasma" onClick={() => void abrirModalAsignar()} icono={<UserPlus className="h-4 w-4" aria-hidden />}>
                      {turno.asignado_a_id ? "Editar asignación" : "Asignar"}
                    </Button>
                  )}
                </>
              )}
            </div>
          </Card>
        ) : (
          <Card titulo="Abrir turno" descripcion="Cuenta el efectivo con el que empieza la caja.">
            <form onSubmit={(e) => void manejarAbrir(e)} className="space-y-4">
              <Input
                label="Efectivo inicial (S/)"
                requerido
                type="number"
                step="0.10"
                min={0}
                inputMode="decimal"
                placeholder="0.00"
                value={montoInicial}
                onChange={(e) => setMontoInicial(e.target.value)}
              />
              <p className="text-xs text-zinc-500">
                Tu apertura queda registrada con tu nombre, fecha y hora, y es visible para
                el resto del equipo. No se puede vender sin un turno abierto.
              </p>
              {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
              <Button type="submit" cargando={procesando} icono={<Wallet className="h-4 w-4" aria-hidden />}>
                Abrir caja
              </Button>
            </form>
          </Card>
        )}
      </div>

      {/* Historial de turnos: ancho completo, con filtro de fecha en el header */}
      <Card
        titulo="Historial de turnos"
        sinPadding
        accion={
          <div className="w-44">
            <DatePicker
              valor={fechaFiltro}
              alCambiar={(f) => setFechaFiltro(f)}
              alineacion="derecha"
              mostrarAnio
              aria-label="Filtrar historial por fecha"
            />
          </div>
        }
      >
        <Table
          columnas={columnas}
          filas={turnosFiltrados}
          claveDe={(t) => t.id}
          vacio={
            <EmptyState
              icono={History}
              titulo="Sin turnos para este día"
              descripcion="No hay turnos registrados en la fecha seleccionada."
            />
          }
        />
      </Card>

      {/* Rastro del turno para la administradora (HU-C08) */}
      <ModalRastroTurno turno={turnoRastro} alCerrar={() => setTurnoRastro(null)} />

      {/* Modal para ver el comentario completo del arqueo */}
      <Modal
        abierto={comentarioModal !== null}
        titulo="Comentario del cierre"
        alCerrar={() => setComentarioModal(null)}
        pie={
          <Button variante="secundario" onClick={() => setComentarioModal(null)}>
            Cerrar
          </Button>
        }
      >
        <p className="whitespace-pre-wrap text-sm text-zinc-700">
          {comentarioModal}
        </p>
      </Modal>

      {/* Modal para asignar turno */}
      <Modal
        abierto={modalAsignar}
        titulo="Editar turno en curso"
        alCerrar={() => setModalAsignar(false)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setModalAsignar(false)} disabled={asignando}>
              Cancelar
            </Button>
            <Button onClick={() => void asignarCajero()} cargando={asignando}>
              Guardar
            </Button>
          </>
        }
      >
        {cargandoCajeros ? (
          <div className="py-8 text-center text-sm text-zinc-500">Cargando datos...</div>
        ) : (
          <div className="space-y-6">
            {errorAsignar && <Alert tono="peligro">{errorAsignar}</Alert>}
            
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">Monto inicial (S/)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={montoInicialEdicion}
                onChange={(e) => setMontoInicialEdicion(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm transition focus:border-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">Asignar a cajero</label>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <button
                  onClick={() => setCajeroSeleccionado(null)}
                  className={`flex items-center gap-3 rounded-lg border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-zinc-900 ${
                    cajeroSeleccionado === null
                      ? "border-zinc-900 bg-zinc-100 ring-1 ring-zinc-900"
                      : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50"
                  }`}
                >
                  <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-medium ${cajeroSeleccionado === null ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-700"}`}>
                    N
                  </div>
                  <div className="overflow-hidden">
                    <p className={`truncate text-sm font-medium ${cajeroSeleccionado === null ? "text-zinc-900" : "text-zinc-900"}`}>Nadie</p>
                    <p className="truncate text-xs text-zinc-500">Sin asignar</p>
                  </div>
                </button>
                {cajeros.map((c) => {
                  const seleccionado = cajeroSeleccionado === c.id;
                  return (
                    <button
                      key={c.id}
                      onClick={() => setCajeroSeleccionado(c.id)}
                      className={`flex items-center gap-3 rounded-lg border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-zinc-900 ${
                        seleccionado
                          ? "border-zinc-900 bg-zinc-100 ring-1 ring-zinc-900"
                          : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50"
                      }`}
                    >
                      <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-medium ${seleccionado ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-700"}`}>
                        {c.nombre.charAt(0).toUpperCase()}
                      </div>
                      <div className="overflow-hidden">
                        <p className={`truncate text-sm font-medium ${seleccionado ? "text-zinc-900" : "text-zinc-900"}`}>{c.nombre}</p>
                        <p className="truncate text-xs text-zinc-500">@{c.username}</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
