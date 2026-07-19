// Modal de RASTRO de un turno (HU-C08): la administradora ve desde su panel de
// caja todo lo que pasó en el turno — ventas, anulaciones, devoluciones y abonos
// de fiado — con quién, cuándo, motivo y cuánto dinero salió del cajón.
import { useEffect, useState } from "react";
import { Badge, Modal, PageSpinner, Alert } from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { cajaHttpAdapter } from "../services/caja.http-adapter";
import type { MovimientosTurno, TurnoCaja } from "../types";

interface Props {
  turno: TurnoCaja | null;
  alCerrar: () => void;
}

function hora(iso: string | null): string {
  return iso ? new Date(iso).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" }) : "—";
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
              <ul className="divide-y divide-zinc-100">
                {datos.ventas.map((v) => (
                  <li key={v.id} className="flex items-center gap-3 py-2 text-sm">
                    <span className="font-mono text-xs text-zinc-400">#{v.id}</span>
                    <span className="text-zinc-500">{hora(v.created_at)}</span>
                    <span className="min-w-0 flex-1 truncate text-zinc-700">
                      {v.items.map((i) => `${i.cantidad}× ${i.nombre}`).join(", ")}
                    </span>
                    <Badge tono="neutro">{v.metodo_pago}</Badge>
                    {v.estado === "ANULADA" && <Badge tono="peligro">Anulada</Badge>}
                    {v.estado === "DEVUELTA_PARCIAL" && <Badge tono="alerta">Dev. parcial</Badge>}
                    <span
                      className={`w-20 text-right font-medium tabular-nums ${
                        v.estado === "ANULADA" ? "text-zinc-400 line-through" : "text-zinc-900"
                      }`}
                    >
                      S/ {v.total.toFixed(2)}
                    </span>
                  </li>
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

          {/* Abonos de fiado cobrados en el turno (HU-C09) */}
          {datos.abonos.length > 0 && (
            <section>
              <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
                Abonos de fiado ({datos.abonos.length})
              </h4>
              <ul className="divide-y divide-zinc-100">
                {datos.abonos.map((a, indice) => (
                  <li key={indice} className="flex items-center gap-3 py-2 text-sm">
                    <span className="min-w-0 flex-1 truncate text-zinc-700">
                      {String(a.cliente ?? "Cliente")} — por {String(a.registrado_por ?? "")}
                    </span>
                    <Badge tono="neutro">{String(a.metodo ?? "")}</Badge>
                    <span className="w-20 text-right font-medium tabular-nums text-green-700">
                      + S/ {Number(a.monto ?? 0).toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </Modal>
  );
}
