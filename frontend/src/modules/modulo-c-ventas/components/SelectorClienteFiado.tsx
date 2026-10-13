// Selector de cliente para fiar desde el cobro: busca entre los clientes o lo
// registra en el momento. Muestra su cuenta y avisa si con esta venta pasa su
// límite mensual (no bloquea: se fía igual y queda la alerta para el admin).
import { useEffect, useMemo, useState } from "react";
import { Search, UserPlus, X } from "lucide-react";
import { Alert, Button, Input } from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { fiadosHttpAdapter } from "../services/fiados.http-adapter";
import type { ClienteFiado } from "../types";

interface Props {
  cliente: ClienteFiado | null;
  alElegir: (cliente: ClienteFiado | null) => void;
  /** Cuánto de esta venta se fía (para avisar si pasa el límite). */
  montoFiado: number;
}

export function SelectorClienteFiado({ cliente, alElegir, montoFiado }: Props) {
  const [clientes, setClientes] = useState<ClienteFiado[]>([]);
  const [buscar, setBuscar] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creando, setCreando] = useState(false);
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [nuevoTelefono, setNuevoTelefono] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    fiadosHttpAdapter
      .listar()
      .then(setClientes)
      .catch((e) => setError(mensajeDeError(e)));
  }, []);

  const filtrados = useMemo(() => {
    const texto = buscar.trim().toLowerCase();
    const lista = texto
      ? clientes.filter(
          (c) => c.nombre.toLowerCase().includes(texto) || (c.telefono ?? "").includes(texto)
        )
      : clientes;
    return lista.slice(0, 6);
  }, [clientes, buscar]);

  async function crear() {
    setGuardando(true);
    setError(null);
    try {
      const nuevo = await fiadosHttpAdapter.crear({
        nombre: nuevoNombre,
        telefono: nuevoTelefono || null,
      });
      setClientes((actual) => [...actual, nuevo]);
      alElegir(nuevo);
      setCreando(false);
      setNuevoNombre("");
      setNuevoTelefono("");
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setGuardando(false);
    }
  }

  if (cliente) {
    const consumoConEsta = cliente.consumo_mes + montoFiado;
    const pasaLimite = montoFiado > 0 && consumoConEsta > cliente.limite_mensual;
    return (
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3 rounded-xl border border-orange-200 bg-orange-50/60 p-3">
          <div className="min-w-0 text-sm">
            <p className="font-medium text-zinc-900">{cliente.nombre}</p>
            <p className="text-zinc-600">
              {cliente.saldo < 0
                ? `Debe S/ ${cliente.deuda.toFixed(2)}`
                : cliente.saldo > 0
                  ? `A favor S/ ${cliente.saldo.toFixed(2)}`
                  : "Sin deuda"}
              {" · "}
              Este mes S/ {cliente.consumo_mes.toFixed(2)} de S/ {cliente.limite_mensual.toFixed(2)}
            </p>
          </div>
          <button
            type="button"
            onClick={() => alElegir(null)}
            aria-label="Cambiar cliente"
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-white hover:text-zinc-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {pasaLimite && (
          <Alert tono="alerta">
            Con esta venta lleva S/ {consumoConEsta.toFixed(2)} fiado este mes y su límite es
            S/ {cliente.limite_mensual.toFixed(2)}. Se fiará igual y quedará la alerta.
          </Alert>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-xl border border-zinc-200 p-3">
      <p className="text-sm font-medium text-zinc-700">¿A quién se le fía?</p>
      {!creando ? (
        <>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={buscar}
              onChange={(e) => setBuscar(e.target.value)}
              placeholder="Buscar cliente por nombre o teléfono…"
              className="h-10 w-full rounded-lg border border-zinc-300 pl-9 pr-3 text-sm outline-none focus:border-zinc-500"
            />
          </div>
          <ul className="max-h-48 space-y-1 overflow-y-auto">
            {filtrados.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => alElegir(c)}
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-zinc-50"
                >
                  <span className="truncate text-zinc-800">{c.nombre}</span>
                  <span
                    className={`shrink-0 tabular-nums text-xs ${c.saldo < 0 ? "text-red-700" : "text-zinc-500"}`}
                  >
                    {c.saldo < 0 ? `debe S/ ${c.deuda.toFixed(2)}` : c.saldo > 0 ? `a favor S/ ${c.saldo.toFixed(2)}` : "al día"}
                  </span>
                </button>
              </li>
            ))}
            {filtrados.length === 0 && (
              <li className="px-3 py-2 text-sm text-zinc-500">No hay clientes con ese nombre.</li>
            )}
          </ul>
          <Button
            variante="secundario"
            compacto
            icono={<UserPlus className="h-4 w-4" />}
            onClick={() => {
              setCreando(true);
              setNuevoNombre(buscar.trim());
            }}
          >
            Registrar cliente nuevo
          </Button>
        </>
      ) : (
        <div className="space-y-2">
          <Input
            label="Nombre"
            value={nuevoNombre}
            onChange={(e) => setNuevoNombre(e.target.value)}
            autoFocus
          />
          <Input
            label="Teléfono (opcional)"
            value={nuevoTelefono}
            inputMode="tel"
            onChange={(e) => setNuevoTelefono(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variante="fantasma" compacto onClick={() => setCreando(false)}>
              Cancelar
            </Button>
            <Button compacto cargando={guardando} disabled={!nuevoNombre.trim()} onClick={() => void crear()}>
              Guardar cliente
            </Button>
          </div>
          <p className="text-xs text-zinc-500">
            El límite mensual lo asigna el administrador desde Fiados.
          </p>
        </div>
      )}
      {error && <Alert tono="peligro">{error}</Alert>}
    </div>
  );
}
