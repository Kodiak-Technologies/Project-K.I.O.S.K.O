// Modal de RASTRO de un turno (HU-C08): la administradora ve desde su panel de
// caja todo lo que pasó en el turno — ventas, anulaciones y devoluciones — con
// quién, cuándo, motivo y cuánto dinero salió del cajón.
import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Badge, Modal, PageSpinner, Alert } from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { cajaHttpAdapter } from "../services/caja.http-adapter";
import type { MovimientosTurno, TurnoCaja, Venta } from "../types";

interface Props {
  turno: TurnoCaja | null;
  alCerrar: () => void;
}

function hora(iso: string | null): string {
  return iso ? new Date(iso).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" }) : "—";
}

// Tarjeta de una venta: colapsada muestra el resumen en una línea (los nombres
// largos se cortan); al hacer clic se despliega la lista completa de productos.
function TarjetaVenta({ venta }: { venta: Venta }) {
  const [abierta, setAbierta] = useState(false);

  return (
    <li className="rounded-lg border border-zinc-200">
      <button
        type="button"
        onClick={() => setAbierta((v) => !v)}
        aria-expanded={abierta}
        className="flex w-full items-center gap-3 rounded-lg p-3 text-left text-sm hover:bg-zinc-50"
      >
        <span className="font-mono text-xs text-zinc-400">#{venta.id}</span>
        <span className="text-zinc-500">{hora(venta.created_at)}</span>
        <span className="min-w-0 flex-1 truncate text-zinc-700">
          {venta.items.map((i) => `${i.cantidad}× ${i.nombre}`).join(", ")}
        </span>
        <Badge tono="neutro">{venta.metodo_pago}</Badge>
        {venta.estado === "ANULADA" && <Badge tono="peligro">Anulada</Badge>}
        {venta.estado === "DEVUELTA_PARCIAL" && <Badge tono="alerta">Dev. parcial</Badge>}
        <span
          className={`w-20 text-right font-medium tabular-nums ${
            venta.estado === "ANULADA" ? "text-zinc-400 line-through" : "text-zinc-900"
          }`}
        >
          S/ {venta.total.toFixed(2)}
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform ${abierta ? "rotate-180" : ""}`}
        />
      </button>
      {abierta && (
        <ul className="divide-y divide-zinc-100 border-t border-zinc-100 px-3">
          {venta.items.map((item, indice) => (
            <li key={item.id ?? indice} className="flex items-center gap-3 py-2 text-sm">
              <span className="w-9 shrink-0 text-right font-mono text-xs text-zinc-500">
                {item.cantidad}×
              </span>
              <span className="min-w-0 flex-1 text-zinc-700">
                {item.nombre}
                {(item.cantidad_devuelta ?? 0) > 0 && (
                  <span className="ml-2 text-xs text-amber-600">
                    ({item.cantidad_devuelta} dev.)
                  </span>
                )}
              </span>
              <span className="shrink-0 text-xs text-zinc-500">
                S/ {item.precio_unitario.toFixed(2)} c/u
              </span>
              <span className="w-20 shrink-0 text-right tabular-nums text-zinc-900">
                S/ {(item.precio_unitario * item.cantidad).toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function ModalRastroTurno({ turno, alCerrar }: Props) {
  const [datos, setDatos] = useState<MovimientosTurno | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDatos(null);
    setError(null);
    if (!turno) return;
    cajaHttpAdapter
      .movimientos(turno.id)
      .then(setDatos)
      .catch((e) => setError(mensajeDeError(e)));
  }, [turno?.id]);

  if (!turno) return null;

  return (
    <Modal
      abierto={turno !== null}
      titulo={`Movimientos del turno #${turno.id} — ${turno.abierto_por}`}
      alCerrar={alCerrar}
    >
      {error && <Alert tono="peligro">{error}</Alert>}
      {!datos && !error && <PageSpinner texto="Cargando movimientos…" />}
      {datos && (
        <div className="space-y-5">
          {/* Ventas del turno */}
          <section>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
              Ventas ({datos.ventas.length})
            </h4>
            {datos.ventas.length === 0 ? (
              <p className="text-sm text-zinc-500">Sin ventas en este turno.</p>
            ) : (
              <ul className="space-y-2">
                {datos.ventas.map((v) => (
                  <TarjetaVenta key={v.id} venta={v} />
                ))}
              </ul>
            )}
          </section>

          {/* Reversos: anulaciones y devoluciones */}
          <section>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
              Anulaciones y devoluciones ({datos.reversos.length})
            </h4>
            {datos.reversos.length === 0 ? (
              <p className="text-sm text-zinc-500">Ningún reverso durante este turno.</p>
            ) : (
              <ul className="space-y-2">
                {datos.reversos.map((r) => (
                  <li key={r.id} className="rounded-lg border border-zinc-200 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tono={r.tipo === "ANULACION" ? "peligro" : "alerta"}>
                        {r.tipo === "ANULACION" ? "Anulación" : "Devolución"}
                      </Badge>
                      <span className="text-zinc-500">
                        venta #{r.venta_id} · {hora(r.created_at)} · por {r.realizado_por}
                      </span>
                      <span className="ml-auto font-medium tabular-nums text-red-700">
                        − S/ {r.monto.toFixed(2)}
                      </span>
                    </div>
                    <p className="mt-1 text-zinc-600">
                      {r.items.map((i) => `${i.cantidad}× ${i.nombre}`).join(", ")}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      Motivo: {r.motivo}
                      {r.efectivo_devuelto > 0 &&
                        ` · Salió del cajón: S/ ${r.efectivo_devuelto.toFixed(2)}`}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </Modal>
  );
}
