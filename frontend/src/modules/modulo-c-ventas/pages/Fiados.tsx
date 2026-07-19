// Página de fiados (HU-C09, RF-28): deudas pendientes agrupadas por cliente,
// registro de abonos (el efectivo entra a la caja del turno actual) y límite de
// crédito por cliente (solo la administradora). Todo deja rastro en bitácora.
import { useMemo, useState } from "react";
import { HandCoins, Wallet } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
} from "../../../shared/components/ui";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useFiados } from "../hooks/useFiados";
import { useMetodosPago } from "../hooks/useMetodosPago";
import type { Fiado } from "../types";

export default function Fiados() {
  const { usuario } = useAuthContext();
  const { fiados, clientes, cargando, error, noDisponible, crearCliente, fijarLimite, abonar } =
    useFiados();
  const { metodos } = useMetodosPago();
  const esAdmin = usuario?.rol === "ADMIN";

  const [paraAbonar, setParaAbonar] = useState<Fiado | null>(null);
  const [montoAbono, setMontoAbono] = useState("");
  const [metodoAbono, setMetodoAbono] = useState("EFECTIVO");
  const [nuevoCliente, setNuevoCliente] = useState("");
  const [limites, setLimites] = useState<Record<number, string>>({});
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  // Reporte de deudas por cliente: los fiados pendientes agrupados.
  const porCliente = useMemo(() => {
    const grupos = new Map<number, { cliente: string; deuda: number; fiados: Fiado[] }>();
    for (const fiado of fiados) {
      const grupo = grupos.get(fiado.cliente_id) ?? {
        cliente: fiado.cliente,
        deuda: 0,
        fiados: [],
      };
      grupo.deuda += fiado.saldo_pendiente;
      grupo.fiados.push(fiado);
      grupos.set(fiado.cliente_id, grupo);
    }
    return [...grupos.entries()].sort((a, b) => b[1].deuda - a[1].deuda);
  }, [fiados]);

  const metodosAbono = metodos.filter((m) => m.codigo !== "FIADO");

  async function manejarAbonar() {
    if (!paraAbonar) return;
    const monto = Number(montoAbono);
    if (Number.isNaN(monto) || monto <= 0) {
      setErrorAccion("Ingresa un monto mayor a 0.");
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      const fiado = await abonar(paraAbonar.id, monto, metodoAbono);
      setMensaje(
        fiado.estado === "PAGADO"
          ? `¡Deuda de ${fiado.cliente} saldada! El abono quedó en la caja del turno.`
          : `Abono de S/ ${monto.toFixed(2)} registrado. ${fiado.cliente} debe S/ ${fiado.saldo_pendiente.toFixed(2)}.`
      );
      setParaAbonar(null);
      setMontoAbono("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  async function manejarCrearCliente() {
    if (!nuevoCliente.trim()) return;
    try {
      await crearCliente({ nombre: nuevoCliente.trim() });
      setNuevoCliente("");
      setMensaje("Cliente registrado.");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
  }

  async function manejarLimite(clienteId: number) {
    const limite = Number(limites[clienteId]);
    if (Number.isNaN(limite) || limite < 0) return;
    try {
      await fijarLimite(clienteId, limite);
      setMensaje("Límite de crédito actualizado.");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Fiados" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas (Módulo C)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando fiados…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const deudaTotal = fiados.reduce((suma, f) => suma + f.saldo_pendiente, 0);

  return (
    <div>
      <PageHeader
        titulo="Fiados"
        descripcion="Cuentas por cobrar: el fiado descuenta stock pero el dinero entra recién con el abono."
        acciones={
          <Badge tono={deudaTotal > 0 ? "alerta" : "exito"}>
            Por cobrar: S/ {deudaTotal.toFixed(2)}
          </Badge>
        }
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        {/* Deudas por cliente */}
        <div className="space-y-4">
          {porCliente.length === 0 ? (
            <Card sinPadding>
              <EmptyState
                icono={HandCoins}
                titulo="Nadie debe nada"
                descripcion="Cuando registres una venta al fiado en el POS aparecerá aquí."
              />
            </Card>
          ) : (
            porCliente.map(([clienteId, grupo]) => (
              <Card key={clienteId} sinPadding>
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-3 sm:px-5">
                  <div>
                    <h3 className="font-semibold text-zinc-900">{grupo.cliente}</h3>
                    <p className="text-sm text-zinc-500">
                      {grupo.fiados.length} {grupo.fiados.length === 1 ? "fiado" : "fiados"} pendientes
                    </p>
                  </div>
                  <span className="text-xl font-semibold tabular-nums text-red-700">
                    S/ {grupo.deuda.toFixed(2)}
                  </span>
                </div>
                <ul className="divide-y divide-zinc-100 px-4 sm:px-5">
                  {grupo.fiados.map((fiado) => (
                    <li key={fiado.id} className="flex items-center gap-3 py-2.5 text-sm">
                      <span className="font-mono text-xs text-zinc-400">venta #{fiado.venta_id}</span>
                      <span className="text-zinc-500">
                        {fiado.created_at
                          ? new Date(fiado.created_at).toLocaleDateString("es-PE")
                          : "—"}
                      </span>
                      <span className="min-w-0 flex-1 text-right text-zinc-500">
                        de S/ {fiado.monto_total.toFixed(2)} debe{" "}
                        <span className="font-medium tabular-nums text-zinc-900">
                          S/ {fiado.saldo_pendiente.toFixed(2)}
                        </span>
                      </span>
                      <Button
                        compacto
                        onClick={() => {
                          setErrorAccion(null);
                          setMontoAbono(fiado.saldo_pendiente.toFixed(2));
                          setParaAbonar(fiado);
                        }}
                        icono={<Wallet className="h-4 w-4" aria-hidden />}
                      >
                        Abonar
                      </Button>
                    </li>
                  ))}
                </ul>
              </Card>
            ))
          )}
        </div>

        {/* Clientes: alta rápida y límites de crédito */}
        <div className="space-y-4">
          <Card titulo="Nuevo cliente">
            <div className="flex items-end gap-2">
              <Input
                label="Nombre"
                placeholder="ej. Don Pedro"
                value={nuevoCliente}
                onChange={(e) => setNuevoCliente(e.target.value)}
              />
              <Button variante="secundario" onClick={() => void manejarCrearCliente()}>
                Crear
              </Button>
            </div>
          </Card>

          <Card
            titulo="Clientes"
            descripcion={esAdmin ? "Fija el límite de crédito (0 = sin límite)." : undefined}
            sinPadding
          >
            {clientes.length === 0 ? (
              <p className="px-5 py-4 text-sm text-zinc-500">Aún no hay clientes registrados.</p>
            ) : (
              <ul className="divide-y divide-zinc-100 px-4 sm:px-5">
                {clientes.map((cliente) => (
                  <li key={cliente.id} className="flex items-center gap-2 py-2.5 text-sm">
                    <span className="min-w-0 flex-1 truncate text-zinc-800">{cliente.nombre}</span>
                    {esAdmin ? (
                      <>
                        <input
                          type="number"
                          min={0}
                          step={10}
                          inputMode="decimal"
                          aria-label={`Límite de crédito de ${cliente.nombre}`}
                          className="w-20 rounded-lg border border-zinc-300 px-2 py-1 text-right text-sm tabular-nums focus:border-zinc-500"
                          placeholder={cliente.limite_credito.toFixed(0)}
                          value={limites[cliente.id] ?? ""}
                          onChange={(e) =>
                            setLimites((actual) => ({ ...actual, [cliente.id]: e.target.value }))
                          }
                        />
                        <Button
                          variante="fantasma"
                          compacto
                          disabled={!limites[cliente.id]}
                          onClick={() => void manejarLimite(cliente.id)}
                        >
                          Fijar
                        </Button>
                      </>
                    ) : (
                      <span className="text-xs text-zinc-400">
                        {cliente.limite_credito > 0
                          ? `límite S/ ${cliente.limite_credito.toFixed(2)}`
                          : "sin límite"}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      {/* Abonar a un fiado */}
      <Modal
        abierto={paraAbonar !== null}
        titulo={`Abono de ${paraAbonar?.cliente ?? ""}`}
        alCerrar={() => setParaAbonar(null)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setParaAbonar(null)}>
              Cancelar
            </Button>
            <Button cargando={procesando} onClick={() => void manejarAbonar()}>
              Registrar abono
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-zinc-600">
            Saldo pendiente:{" "}
            <span className="font-medium tabular-nums">
              S/ {paraAbonar?.saldo_pendiente.toFixed(2)}
            </span>
            . El dinero del abono entra a la caja del turno abierto.
          </p>
          <Input
            label="Monto del abono (S/)"
            requerido
            type="number"
            step="0.10"
            min={0}
            inputMode="decimal"
            value={montoAbono}
            onChange={(e) => setMontoAbono(e.target.value)}
          />
          <Select
            label="Método de pago"
            value={metodoAbono}
            onChange={(e) => setMetodoAbono(e.target.value)}
          >
            {metodosAbono.map((m) => (
              <option key={m.codigo} value={m.codigo}>
                {m.nombre}
              </option>
            ))}
          </Select>
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
        </div>
      </Modal>
    </div>
  );
}
