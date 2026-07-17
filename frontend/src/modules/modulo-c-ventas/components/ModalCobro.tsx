// Modal de cobro del POS (HU-C04, RF-20): ninguna venta se confirma sin método
// de pago. Métodos desde el catálogo del backend (el ADMIN puede agregar más),
// pago mixto (dividir entre varios métodos) y cálculo del vuelto en efectivo.
import { useMemo, useState } from "react";
import { Coins, SplitSquareHorizontal } from "lucide-react";
import { Alert, Button, Input, Modal } from "../../../shared/components/ui";
import { useMetodosPago } from "../hooks/useMetodosPago";
import type { NuevoPago } from "../types";

interface Props {
  abierto: boolean;
  total: number;
  procesando: boolean;
  error: string | null;
  alCerrar: () => void;
  alConfirmar: (pagos: NuevoPago[]) => void;
}

export function ModalCobro({ abierto, total, procesando, error, alCerrar, alConfirmar }: Props) {
  const { metodos } = useMetodosPago();
  // El fiado tiene su propio flujo con cliente (HU-C09); aquí solo pagos normales.
  const seleccionables = useMemo(() => metodos.filter((m) => m.codigo !== "FIADO"), [metodos]);

  const [mixto, setMixto] = useState(false);
  const [metodoSimple, setMetodoSimple] = useState("EFECTIVO");
  const [recibido, setRecibido] = useState("");
  const [montosMixto, setMontosMixto] = useState<Record<string, string>>({});

  const infoSimple = seleccionables.find((m) => m.codigo === metodoSimple);
  const recibidoNum = Number(recibido);

  // --- pago simple: un método por el total ---
  const vueltoSimple =
    infoSimple?.es_efectivo && recibido !== "" && !Number.isNaN(recibidoNum)
      ? recibidoNum - total
      : null;
  const simpleValido =
    infoSimple !== undefined &&
    (!infoSimple.es_efectivo || recibido === "" || (vueltoSimple !== null && vueltoSimple >= 0));

  // --- pago mixto: la suma debe cuadrar exacto con el total (RNF-03) ---
  const sumaMixto = seleccionables.reduce((suma, m) => {
    const monto = Number(montosMixto[m.codigo]);
    return suma + (Number.isNaN(monto) ? 0 : monto);
  }, 0);
  const restante = Math.round((total - sumaMixto) * 100) / 100;
  const montoEfectivoMixto = seleccionables
    .filter((m) => m.es_efectivo)
    .reduce((suma, m) => suma + (Number(montosMixto[m.codigo]) || 0), 0);
  const vueltoMixto =
    montoEfectivoMixto > 0 && recibido !== "" && !Number.isNaN(recibidoNum)
      ? recibidoNum - montoEfectivoMixto
      : null;
  const mixtoValido = restante === 0 && sumaMixto > 0 && (vueltoMixto === null || vueltoMixto >= 0);

  function reiniciar() {
    setMixto(false);
    setMetodoSimple("EFECTIVO");
    setRecibido("");
    setMontosMixto({});
  }

  function confirmar() {
    if (mixto) {
      const pagos: NuevoPago[] = seleccionables
        .filter((m) => Number(montosMixto[m.codigo]) > 0)
        .map((m) => ({
          metodo: m.codigo,
          monto: Number(montosMixto[m.codigo]),
          ...(m.es_efectivo && recibido !== "" ? { monto_recibido: recibidoNum } : {}),
        }));
      alConfirmar(pagos);
    } else {
      alConfirmar([
        {
          metodo: metodoSimple,
          ...(infoSimple?.es_efectivo && recibido !== "" ? { monto_recibido: recibidoNum } : {}),
        },
      ]);
    }
  }

  const vuelto = mixto ? vueltoMixto : vueltoSimple;

  return (
    <Modal
      abierto={abierto}
      titulo={`Cobrar S/ ${total.toFixed(2)}`}
      alCerrar={() => {
        reiniciar();
        alCerrar();
      }}
      pie={
        <>
          <Button
            variante="secundario"
            onClick={() => {
              reiniciar();
              alCerrar();
            }}
          >
            Cancelar
          </Button>
          <Button
            cargando={procesando}
            disabled={mixto ? !mixtoValido : !simpleValido}
            onClick={confirmar}
          >
            Confirmar venta
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Selector simple / mixto */}
        <div className="flex rounded-lg border border-zinc-200 p-0.5">
          <button
            type="button"
            onClick={() => setMixto(false)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ${
              !mixto ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-50"
            }`}
          >
            <Coins className="h-4 w-4" aria-hidden /> Un solo método
          </button>
          <button
            type="button"
            onClick={() => setMixto(true)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ${
              mixto ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-50"
            }`}
          >
            <SplitSquareHorizontal className="h-4 w-4" aria-hidden /> Pago mixto
          </button>
        </div>

        {!mixto ? (
          <>
            {/* Botones grandes: rápido para tocar en caja */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {seleccionables.map((m) => (
                <button
                  key={m.codigo}
                  type="button"
                  onClick={() => setMetodoSimple(m.codigo)}
                  className={`min-h-tactil rounded-xl border px-2 py-2 text-sm font-medium transition-colors ${
                    metodoSimple === m.codigo
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400"
                  }`}
                >
                  {m.nombre}
                </button>
              ))}
            </div>
            {infoSimple?.es_efectivo && (
              <Input
                label="¿Con cuánto paga? (S/) — opcional, para el vuelto"
                type="number"
                step="0.10"
                min={0}
                inputMode="decimal"
                placeholder={total.toFixed(2)}
                value={recibido}
                onChange={(e) => setRecibido(e.target.value)}
                error={vueltoSimple !== null && vueltoSimple < 0 ? "No alcanza para cubrir el total." : null}
              />
            )}
          </>
        ) : (
          <>
            <p className="text-sm text-zinc-500">
              Divide el total entre los métodos usados. La suma debe cuadrar exacto.
            </p>
            <div className="space-y-2">
              {seleccionables.map((m) => (
                <div key={m.codigo} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 text-sm text-zinc-700">{m.nombre}</span>
                  <Input
                    type="number"
                    step="0.10"
                    min={0}
                    inputMode="decimal"
                    placeholder="0.00"
                    value={montosMixto[m.codigo] ?? ""}
                    onChange={(e) =>
                      setMontosMixto((actual) => ({ ...actual, [m.codigo]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
            <p className={`text-sm font-medium ${restante === 0 ? "text-green-700" : "text-red-700"}`}>
              {restante > 0
                ? `Falta repartir S/ ${restante.toFixed(2)}`
                : restante < 0
                  ? `Sobran S/ ${Math.abs(restante).toFixed(2)}`
                  : "Los pagos cuadran con el total ✓"}
            </p>
            {montoEfectivoMixto > 0 && (
              <Input
                label={`¿Con cuánto paga el efectivo (S/ ${montoEfectivoMixto.toFixed(2)})? — opcional`}
                type="number"
                step="0.10"
                min={0}
                inputMode="decimal"
                placeholder={montoEfectivoMixto.toFixed(2)}
                value={recibido}
                onChange={(e) => setRecibido(e.target.value)}
                error={vueltoMixto !== null && vueltoMixto < 0 ? "No alcanza para cubrir el efectivo." : null}
              />
            )}
          </>
        )}

        {vuelto !== null && vuelto >= 0 && (
          <div className="flex items-center justify-between rounded-lg bg-zinc-50 px-3 py-2.5">
            <span className="text-sm text-zinc-600">Vuelto a entregar</span>
            <span className="text-xl font-semibold tabular-nums text-zinc-900">
              S/ {vuelto.toFixed(2)}
            </span>
          </div>
        )}

        {error && <Alert tono="peligro">{error}</Alert>}
      </div>
    </Modal>
  );
}
