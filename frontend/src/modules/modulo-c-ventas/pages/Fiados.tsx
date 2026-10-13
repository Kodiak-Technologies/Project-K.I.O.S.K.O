// Fiados: a quién se le fió, cuánto debe, su crédito y todo su estado de cuenta.
// Todos lo ven y pueden registrar pagos (entran a la caja del turno actual).
// Solo el ADMIN asigna el límite mensual y registra créditos ya pagados.
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, HandCoins, Search, UserPlus, Users, Wallet } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  PageHeader,
  PageSpinner,
  Select,
} from "../../../shared/components/ui";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useMetodosPago } from "../hooks/useMetodosPago";
import { fiadosHttpAdapter } from "../services/fiados.http-adapter";
import type { ClienteFiado, EstadoCuentaFiado, MovimientoFiado } from "../types";

function soles(monto: number): string {
  return `S/ ${monto.toFixed(2)}`;
}

function fechaHora(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" })
    : "—";
}

function TextoSaldo({ cliente }: { cliente: ClienteFiado }) {
  if (cliente.saldo < 0) return <span className="font-semibold text-red-700">Debe {soles(cliente.deuda)}</span>;
  if (cliente.saldo > 0) return <span className="font-semibold text-blue-700">A favor {soles(cliente.saldo)}</span>;
  return <span className="text-zinc-500">Al día</span>;
}

// Barra del consumo del mes contra el límite: se pone ámbar cerca y roja al pasarlo.
function BarraLimite({ cliente }: { cliente: ClienteFiado }) {
  const porcentaje =
    cliente.limite_mensual > 0 ? Math.min((cliente.consumo_mes / cliente.limite_mensual) * 100, 100) : 100;
  const color = cliente.excede_limite ? "bg-red-500" : porcentaje >= 80 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
        <div
          className={`h-full ${cliente.consumo_mes > 0 ? color : ""}`}
          style={{ width: `${cliente.consumo_mes > 0 ? porcentaje : 0}%` }}
        />
      </div>
      <p className="mt-1 text-xs tabular-nums text-zinc-500">
        Este mes {soles(cliente.consumo_mes)} de {soles(cliente.limite_mensual)}
      </p>
    </div>
  );
}

const ESTILO_MOVIMIENTO: Record<MovimientoFiado["tipo"], { etiqueta: string; tono: "peligro" | "exito" | "info" | "neutro"; signo: string; clase: string }> = {
  CONSUMO: { etiqueta: "Fiado", tono: "peligro", signo: "−", clase: "text-red-700" },
  PAGO: { etiqueta: "Pago", tono: "exito", signo: "+", clase: "text-emerald-700" },
  ADELANTO: { etiqueta: "Crédito pagado", tono: "info", signo: "+", clase: "text-blue-700" },
  REVERSO: { etiqueta: "Anulación / devolución", tono: "neutro", signo: "+", clase: "text-zinc-700" },
};

function FilaMovimiento({ m }: { m: MovimientoFiado }) {
  const estilo = ESTILO_MOVIMIENTO[m.tipo];
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 text-sm">
      <Badge tono={estilo.tono}>{estilo.etiqueta}</Badge>
      <span className="text-xs text-zinc-500">{fechaHora(m.created_at)}</span>
      <span className="min-w-0 flex-1 truncate text-xs text-zinc-500">
        {m.venta_id ? `Venta #${m.venta_id}` : ""}
        {m.entra_a_caja && m.metodo ? `${m.venta_id ? " · " : ""}${m.metodo} · turno #${m.turno_id}` : ""}
        {m.nota ? ` · ${m.nota}` : ""}
        {` · por ${m.registrado_por}`}
      </span>
      <span className={`shrink-0 font-medium tabular-nums ${estilo.clase}`}>
        {estilo.signo} {soles(m.monto)}
      </span>
      <span className="w-28 shrink-0 text-right text-xs tabular-nums text-zinc-400">
        saldo {soles(m.saldo_resultante)}
      </span>
    </li>
  );
}

type Accion = "pago" | "credito" | "editar" | null;

// Detalle de la cuenta: estado de cuenta completo + acciones.
function ModalCuenta({
  clienteId,
  esAdmin,
  alCerrar,
  alCambiar,
}: {
  clienteId: number | null;
  esAdmin: boolean;
  alCerrar: () => void;
  alCambiar: () => void;
}) {
  const { metodos } = useMetodosPago();
  const [datos, setDatos] = useState<EstadoCuentaFiado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accion, setAccion] = useState<Accion>(null);
  const [monto, setMonto] = useState("");
  const [metodo, setMetodo] = useState("EFECTIVO");
  const [nota, setNota] = useState("");
  const [edicion, setEdicion] = useState({ nombre: "", telefono: "", nota: "", limite: "", activo: true });
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    if (clienteId === null) return;
    try {
      setDatos(await fiadosHttpAdapter.estadoDeCuenta(clienteId));
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }, [clienteId]);

  useEffect(() => {
    setDatos(null);
    setError(null);
    setAccion(null);
    void cargar();
  }, [cargar]);

  function abrir(nueva: Accion) {
    setError(null);
    setAccion(nueva);
    setNota("");
    setMetodo("EFECTIVO");
    if (nueva === "pago" && datos) setMonto(datos.cliente.deuda.toFixed(2));
    if (nueva === "credito") setMonto("");
    if (nueva === "editar" && datos) {
      setEdicion({
        nombre: datos.cliente.nombre,
        telefono: datos.cliente.telefono ?? "",
        nota: datos.cliente.nota ?? "",
        limite: datos.cliente.limite_mensual.toFixed(2),
        activo: datos.cliente.activo,
      });
    }
  }

  async function guardar() {
    if (!datos) return;
    setGuardando(true);
    setError(null);
    try {
      const id = datos.cliente.id;
      if (accion === "pago") await fiadosHttpAdapter.pagar(id, Number(monto), metodo, nota || undefined);
      if (accion === "credito") await fiadosHttpAdapter.creditoPagado(id, Number(monto), metodo, nota || undefined);
      if (accion === "editar") {
        await fiadosHttpAdapter.actualizar(id, {
          nombre: edicion.nombre,
          telefono: edicion.telefono || null,
          nota: edicion.nota || null,
          ...(esAdmin ? { limite_mensual: Number(edicion.limite) || 0, activo: edicion.activo } : {}),
        });
      }
      setAccion(null);
      await cargar();
      alCambiar();
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setGuardando(false);
    }
  }

  const cliente = datos?.cliente;
  const montoValido = Number(monto) > 0;

  return (
    <Modal
      abierto={clienteId !== null}
      titulo={cliente ? `Cuenta de ${cliente.nombre}` : "Cuenta del cliente"}
      alCerrar={alCerrar}
      ancho="sm:max-w-2xl"
    >
      {!datos && !error && <PageSpinner texto="Cargando cuenta…" />}
      {error && !accion && <Alert tono="peligro">{error}</Alert>}
      {cliente && datos && (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-zinc-200 p-3">
              <p className="text-xs uppercase tracking-wide text-zinc-400">Saldo</p>
              <p className="mt-1 text-lg">
                <TextoSaldo cliente={cliente} />
              </p>
            </div>
            <div className="rounded-xl border border-zinc-200 p-3 sm:col-span-2">
              <p className="mb-1 text-xs uppercase tracking-wide text-zinc-400">Límite mensual</p>
              <BarraLimite cliente={cliente} />
              {cliente.excede_limite && (
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-red-700">
                  <AlertTriangle className="h-3.5 w-3.5" /> Pasó su límite este mes
                </p>
              )}
            </div>
          </div>
          {(cliente.telefono || cliente.nota) && (
            <p className="text-sm text-zinc-600">
              {cliente.telefono && `Tel. ${cliente.telefono}`}
              {cliente.telefono && cliente.nota && " · "}
              {cliente.nota}
            </p>
          )}

          {accion === null ? (
            <div className="flex flex-wrap gap-2">
              <Button icono={<HandCoins className="h-4 w-4" />} disabled={cliente.deuda <= 0} onClick={() => abrir("pago")}>
                Registrar pago
              </Button>
              {esAdmin && (
                <Button variante="secundario" icono={<Wallet className="h-4 w-4" />} onClick={() => abrir("credito")}>
                  Crédito ya pagado
                </Button>
              )}
              <Button variante="fantasma" onClick={() => abrir("editar")}>
                Editar
              </Button>
            </div>
          ) : (
            <div className="space-y-3 rounded-xl border border-zinc-200 bg-zinc-50/60 p-3">
              {accion === "editar" ? (
                <>
                  <Input label="Nombre" value={edicion.nombre} onChange={(e) => setEdicion({ ...edicion, nombre: e.target.value })} />
                  <Input label="Teléfono" value={edicion.telefono} onChange={(e) => setEdicion({ ...edicion, telefono: e.target.value })} />
                  <Input label="Nota" value={edicion.nota} onChange={(e) => setEdicion({ ...edicion, nota: e.target.value })} />
                  {esAdmin && (
                    <>
                      <Input
                        label="Límite mensual (S/)"
                        type="number"
                        min={0}
                        step="0.10"
                        inputMode="decimal"
                        value={edicion.limite}
                        onChange={(e) => setEdicion({ ...edicion, limite: e.target.value })}
                      />
                      <label className="flex items-center gap-2 text-sm text-zinc-700">
                        <input
                          type="checkbox"
                          checked={edicion.activo}
                          onChange={(e) => setEdicion({ ...edicion, activo: e.target.checked })}
                        />
                        Cliente activo (se le puede fiar)
                      </label>
                    </>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm text-zinc-600">
                    {accion === "pago"
                      ? `Debe ${soles(cliente.deuda)}. El pago entra a la caja del turno actual.`
                      : "Lo que ya pagó por adelantado: queda a favor del cliente y entra a la caja del turno actual."}
                  </p>
                  <Input
                    label="Monto (S/)"
                    type="number"
                    min={0}
                    step="0.10"
                    inputMode="decimal"
                    value={monto}
                    onChange={(e) => setMonto(e.target.value)}
                  />
                  <Select
                    label="Método"
                    value={metodo}
                    onSelectValue={(v) => setMetodo(String(v))}
                    opciones={metodos.map((m) => ({ value: m.codigo, label: m.nombre }))}
                  />
                  <Input label="Nota (opcional)" value={nota} onChange={(e) => setNota(e.target.value)} />
                </>
              )}
              {error && <Alert tono="peligro">{error}</Alert>}
              <div className="flex justify-end gap-2">
                <Button variante="secundario" onClick={() => setAccion(null)}>
                  Cancelar
                </Button>
                <Button
                  cargando={guardando}
                  disabled={accion === "editar" ? !edicion.nombre.trim() : !montoValido}
                  onClick={() => void guardar()}
                >
                  Guardar
                </Button>
              </div>
            </div>
          )}

          <section>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Movimientos ({datos.movimientos.length})
            </h4>
            {datos.movimientos.length === 0 ? (
              <p className="text-sm text-zinc-500">Todavía no tiene movimientos.</p>
            ) : (
              <ul className="divide-y divide-zinc-100">
                {datos.movimientos.map((m) => (
                  <FilaMovimiento key={m.id} m={m} />
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </Modal>
  );
}

function ModalNuevoCliente({
  abierto,
  esAdmin,
  alCerrar,
  alCrear,
}: {
  abierto: boolean;
  esAdmin: boolean;
  alCerrar: () => void;
  alCrear: (cliente: ClienteFiado) => void;
}) {
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [nota, setNota] = useState("");
  const [limite, setLimite] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cerrar() {
    setNombre("");
    setTelefono("");
    setNota("");
    setLimite("");
    setError(null);
    alCerrar();
  }

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      const cliente = await fiadosHttpAdapter.crear({
        nombre,
        telefono: telefono || null,
        nota: nota || null,
        ...(esAdmin && limite ? { limite_mensual: Number(limite) } : {}),
      });
      cerrar();
      alCrear(cliente);
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal
      abierto={abierto}
      titulo="Nuevo cliente de fiado"
      alCerrar={cerrar}
      pie={
        <>
          <Button variante="secundario" onClick={cerrar}>
            Cancelar
          </Button>
          <Button cargando={guardando} disabled={!nombre.trim()} onClick={() => void guardar()}>
            Guardar
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Input label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} autoFocus />
        <Input label="Teléfono (opcional)" value={telefono} inputMode="tel" onChange={(e) => setTelefono(e.target.value)} />
        <Input label="Nota (opcional)" value={nota} onChange={(e) => setNota(e.target.value)} />
        {esAdmin ? (
          <Input
            label="Límite mensual (S/)"
            type="number"
            min={0}
            step="0.10"
            inputMode="decimal"
            placeholder="0.00"
            value={limite}
            onChange={(e) => setLimite(e.target.value)}
          />
        ) : (
          <p className="text-xs text-zinc-500">El límite mensual lo asigna el administrador.</p>
        )}
        {error && <Alert tono="peligro">{error}</Alert>}
      </div>
    </Modal>
  );
}

export default function Fiados() {
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";
  const [clientes, setClientes] = useState<ClienteFiado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [buscar, setBuscar] = useState("");
  const [verInactivos, setVerInactivos] = useState(false);
  const [seleccionado, setSeleccionado] = useState<number | null>(null);
  const [nuevo, setNuevo] = useState(false);

  const recargar = useCallback(async () => {
    try {
      setClientes(await fiadosHttpAdapter.listar(undefined, verInactivos));
      setError(null);
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }, [verInactivos]);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const filtrados = useMemo(() => {
    const texto = buscar.trim().toLowerCase();
    if (!clientes) return [];
    return texto
      ? clientes.filter((c) => c.nombre.toLowerCase().includes(texto) || (c.telefono ?? "").includes(texto))
      : clientes;
  }, [clientes, buscar]);

  const resumen = useMemo(() => {
    const lista = clientes ?? [];
    return {
      porCobrar: lista.reduce((s, c) => s + c.deuda, 0),
      conDeuda: lista.filter((c) => c.deuda > 0).length,
      sobreLimite: lista.filter((c) => c.excede_limite).length,
    };
  }, [clientes]);

  return (
    <div>
      <PageHeader
        titulo="Fiados"
        descripcion="A quién se le fió, cuánto debe y sus pagos. Lo fiado entra a la caja recién cuando lo pagan."
        acciones={
          <Button icono={<UserPlus className="h-4 w-4" />} onClick={() => setNuevo(true)}>
            Nuevo cliente
          </Button>
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Card>
          <p className="text-xs uppercase tracking-wide text-zinc-400">Por cobrar</p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-red-700">{soles(resumen.porCobrar)}</p>
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-wide text-zinc-400">Clientes con deuda</p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-zinc-900">{resumen.conDeuda}</p>
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-wide text-zinc-400">Pasaron su límite este mes</p>
          <p className={`mt-1 text-xl font-semibold tabular-nums ${resumen.sobreLimite > 0 ? "text-amber-600" : "text-zinc-900"}`}>
            {resumen.sobreLimite}
          </p>
        </Card>
      </div>

      <Card sinPadding>
        <div className="flex flex-wrap items-center gap-3 border-b border-zinc-100 p-3 sm:p-4">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={buscar}
              onChange={(e) => setBuscar(e.target.value)}
              placeholder="Buscar por nombre o teléfono…"
              className="h-10 w-full rounded-lg border border-zinc-300 pl-9 pr-3 text-sm outline-none focus:border-zinc-500"
            />
          </div>
          {esAdmin && (
            <label className="flex items-center gap-2 text-sm text-zinc-600">
              <input type="checkbox" checked={verInactivos} onChange={(e) => setVerInactivos(e.target.checked)} />
              Ver desactivados
            </label>
          )}
        </div>

        {error && (
          <div className="p-4">
            <Alert tono="peligro">{error}</Alert>
          </div>
        )}
        {!clientes && !error && <PageSpinner texto="Cargando clientes…" />}
        {clientes && filtrados.length === 0 && (
          <EmptyState
            icono={Users}
            titulo={clientes.length === 0 ? "Aún no hay clientes de fiado" : "Sin resultados"}
            descripcion={
              clientes.length === 0
                ? "Regístralos aquí o directamente al cobrar con Fiado."
                : "Prueba con otro nombre o teléfono."
            }
          />
        )}
        {filtrados.length > 0 && (
          <ul className="divide-y divide-zinc-100">
            {filtrados.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSeleccionado(c.id)}
                  className="grid w-full gap-2 p-3 text-left hover:bg-zinc-50 sm:grid-cols-[1fr_auto_14rem] sm:items-center sm:gap-4 sm:p-4"
                >
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 truncate font-medium text-zinc-900">
                      {c.nombre}
                      {!c.activo && <Badge tono="neutro">Desactivado</Badge>}
                      {c.excede_limite && <Badge tono="alerta">Sobre el límite</Badge>}
                    </p>
                    {c.telefono && <p className="text-xs text-zinc-500">{c.telefono}</p>}
                  </div>
                  <div className="text-sm sm:text-right">
                    <TextoSaldo cliente={c} />
                  </div>
                  <BarraLimite cliente={c} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <ModalCuenta
        clienteId={seleccionado}
        esAdmin={esAdmin}
        alCerrar={() => setSeleccionado(null)}
        alCambiar={() => void recargar()}
      />
      <ModalNuevoCliente
        abierto={nuevo}
        esAdmin={esAdmin}
        alCerrar={() => setNuevo(false)}
        alCrear={(cliente) => {
          void recargar();
          setSeleccionado(cliente.id);
        }}
      />
    </div>
  );
}
