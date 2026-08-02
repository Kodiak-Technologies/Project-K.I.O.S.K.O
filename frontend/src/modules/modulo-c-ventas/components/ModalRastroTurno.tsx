// Modal de RASTRO de un turno (HU-C08): la administradora ve desde su panel de
// caja todo lo que pasó en el turno — ventas, anulaciones y devoluciones — con
// quién, cuándo, motivo y cuánto dinero salió del cajón.
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRightLeft,
  Banknote,
  ChevronDown,
  CreditCard,
  DollarSign,
  Receipt,
  Smartphone,
} from "lucide-react";
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

export interface TotalesDesglose {
  porMetodo: Record<string, number>;
  totalNeto: number;
  totalBruto: number;
  totalDevoluciones: number;
}

function calcularTotalesTurno(movimientos: MovimientosTurno): TotalesDesglose {
  const porMetodo: Record<string, number> = {};
  let totalBruto = 0;
  let totalDevoluciones = 0;

  for (const v of movimientos.ventas) {
    if (v.anulada || v.estado === "ANULADA") continue;

    if (v.pagos && v.pagos.length > 0) {
      for (const p of v.pagos) {
        const metodo = p.metodo.toUpperCase();
        porMetodo[metodo] = (porMetodo[metodo] || 0) + p.monto;
        totalBruto += p.monto;
      }
    } else {
      const metodo = (v.metodo_pago || "EFECTIVO").toUpperCase();
      const monto = v.total || 0;
      porMetodo[metodo] = (porMetodo[metodo] || 0) + monto;
      totalBruto += monto;
    }
  }

  for (const r of movimientos.reversos) {
    const montoReverso = r.monto || 0;
    const ventaOrigen = movimientos.ventas.find((v) => v.id === r.venta_id);

    if (r.tipo === "DEVOLUCION") {
      totalDevoluciones += montoReverso;
      if (r.efectivo_devuelto && r.efectivo_devuelto > 0) {
        const efecDev = r.efectivo_devuelto;
        porMetodo["EFECTIVO"] = (porMetodo["EFECTIVO"] || 0) - efecDev;
        const remanente = montoReverso - efecDev;
        if (remanente > 0 && ventaOrigen) {
          const metodoOtro = (
            ventaOrigen.pagos && ventaOrigen.pagos.length > 0
              ? ventaOrigen.pagos.find((p) => p.metodo.toUpperCase() !== "EFECTIVO")?.metodo
              : ventaOrigen.metodo_pago
          )?.toUpperCase() || "EFECTIVO";
          porMetodo[metodoOtro] = (porMetodo[metodoOtro] || 0) - remanente;
        }
      } else {
        const metodoVenta = (
          ventaOrigen?.pagos && ventaOrigen.pagos.length > 0
            ? ventaOrigen.pagos[0].metodo
            : ventaOrigen?.metodo_pago || "EFECTIVO"
        ).toUpperCase();
        porMetodo[metodoVenta] = (porMetodo[metodoVenta] || 0) - montoReverso;
      }
    } else if (r.tipo === "ANULACION") {
      if (ventaOrigen && !ventaOrigen.anulada && ventaOrigen.estado !== "ANULADA") {
        totalDevoluciones += montoReverso;
        const metodoVenta = (
          ventaOrigen.pagos && ventaOrigen.pagos.length > 0
            ? ventaOrigen.pagos[0].metodo
            : ventaOrigen.metodo_pago || "EFECTIVO"
        ).toUpperCase();
        porMetodo[metodoVenta] = (porMetodo[metodoVenta] || 0) - montoReverso;
      }
    }
  }

  if (porMetodo["EFECTIVO"] === undefined) {
    porMetodo["EFECTIVO"] = 0;
  }

  const totalNeto = totalBruto - totalDevoluciones;

  return {
    porMetodo,
    totalNeto,
    totalBruto,
    totalDevoluciones,
  };
}

function infoEstiloMetodo(metodo: string) {
  const m = (metodo || "EFECTIVO").toUpperCase();
  if (m === "EFECTIVO") {
    return {
      etiqueta: "Efectivo",
      icono: Banknote,
      claseCard: "bg-emerald-50/80 border-emerald-200 text-emerald-950",
      claseIcono: "bg-emerald-100/90 text-emerald-700",
      claseMonto: "text-emerald-700",
      pillClass: "bg-emerald-50 border-emerald-200 text-emerald-700",
      dotClass: "bg-emerald-500",
    };
  }
  if (m === "YAPE") {
    return {
      etiqueta: "Yape",
      icono: Smartphone,
      claseCard: "bg-purple-50/80 border-purple-200 text-purple-950",
      claseIcono: "bg-purple-100/90 text-purple-700",
      claseMonto: "text-purple-700",
      pillClass: "bg-purple-50 border-purple-200 text-purple-700",
      dotClass: "bg-purple-500",
    };
  }
  if (m === "PLIN") {
    return {
      etiqueta: "Plin",
      icono: Smartphone,
      claseCard: "bg-amber-50/80 border-amber-200 text-amber-950",
      claseIcono: "bg-amber-100/90 text-amber-700",
      claseMonto: "text-amber-700",
      pillClass: "bg-amber-50 border-amber-200 text-amber-700",
      dotClass: "bg-amber-500",
    };
  }
  if (m === "TRANSFERENCIA") {
    return {
      etiqueta: "Transferencia",
      icono: ArrowRightLeft,
      claseCard: "bg-blue-50/80 border-blue-200 text-blue-950",
      claseIcono: "bg-blue-100/90 text-blue-700",
      claseMonto: "text-blue-700",
      pillClass: "bg-blue-50 border-blue-200 text-blue-700",
      dotClass: "bg-blue-500",
    };
  }
  if (m === "TARJETA") {
    return {
      etiqueta: "Tarjeta",
      icono: CreditCard,
      claseCard: "bg-zinc-100/80 border-zinc-300 text-zinc-950",
      claseIcono: "bg-zinc-200 text-zinc-700",
      claseMonto: "text-zinc-900",
      pillClass: "bg-zinc-100 border-zinc-300 text-zinc-800",
      dotClass: "bg-zinc-600",
    };
  }
  if (m === "MIXTO") {
    return {
      etiqueta: "Mixto",
      icono: Receipt,
      claseCard: "bg-pink-50/80 border-pink-200 text-pink-950",
      claseIcono: "bg-pink-100/90 text-pink-700",
      claseMonto: "text-pink-700",
      pillClass: "bg-pink-50 border-pink-200 text-pink-700",
      dotClass: "bg-pink-500",
    };
  }
  return {
    etiqueta: metodo,
    icono: Receipt,
    claseCard: "bg-zinc-50 border-zinc-200 text-zinc-900",
    claseIcono: "bg-zinc-200 text-zinc-700",
    claseMonto: "text-zinc-900",
    pillClass: "bg-zinc-100 border-zinc-200 text-zinc-700",
    dotClass: "bg-zinc-500",
  };
}

function BadgeMetodoPago({ metodo }: { metodo: string }) {
  const info = infoEstiloMetodo(metodo);
  return (
    <>
      {/* En teléfono (mobile): solo un punto del color del método para no empujar el monto */}
      <span
        title={metodo}
        className={`inline-flex sm:hidden h-2.5 w-2.5 shrink-0 rounded-full ${info.dotClass}`}
      />

      {/* En desktop: la píldora que encierra el texto con su color del método */}
      <span
        className={`hidden sm:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold shrink-0 ${info.pillClass}`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${info.dotClass}`} />
        {metodo}
      </span>
    </>
  );
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
        className="flex w-full items-center gap-2 sm:gap-3 rounded-lg p-2.5 sm:p-3 text-left text-sm hover:bg-zinc-50"
      >
        <span className="font-mono text-xs text-zinc-400 shrink-0">#{venta.id}</span>
        <span className="text-xs sm:text-sm text-zinc-500 shrink-0 whitespace-nowrap">{hora(venta.created_at)}</span>
        <span className="min-w-0 flex-1 truncate text-zinc-700 text-xs sm:text-sm">
          {venta.items.map((i) => `${i.cantidad}× ${i.nombre}`).join(", ")}
        </span>

        <BadgeMetodoPago metodo={venta.metodo_pago} />

        {venta.estado === "ANULADA" && <Badge tono="peligro">Anulada</Badge>}
        {venta.estado === "DEVUELTA_PARCIAL" && <Badge tono="alerta">Dev. parcial</Badge>}

        <span
          className={`shrink-0 whitespace-nowrap text-right text-xs sm:text-sm font-medium tabular-nums ${
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
        <div className="border-t border-zinc-100 bg-zinc-50/50">
          {(venta.metodo_pago === "MIXTO" || (venta.pagos && venta.pagos.length > 1)) && (
            <div className="border-b border-zinc-100 bg-white/80 px-3 py-2.5 sm:px-4">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                Desglose de Pago Mixto:
              </span>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {venta.pagos && venta.pagos.length > 0 ? (
                  venta.pagos.map((pago, pIdx) => {
                    const infoP = infoEstiloMetodo(pago.metodo);
                    return (
                      <div
                        key={pIdx}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium ${infoP.pillClass}`}
                      >
                        <span className={`h-2 w-2 rounded-full ${infoP.dotClass}`} />
                        <span>{infoP.etiqueta}:</span>
                        <span className="font-bold tabular-nums">
                          S/ {pago.monto.toFixed(2)}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <span className="text-zinc-500 italic">Sin desglose de pagos disponible</span>
                )}
              </div>
            </div>
          )}

          <ul className="divide-y divide-zinc-100 px-3">
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
        </div>
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

  const totales = useMemo(() => (datos ? calcularTotalesTurno(datos) : null), [datos]);

  const metodosKeys = useMemo(() => {
    if (!totales) return [];
    const orden = ["EFECTIVO", "YAPE", "PLIN", "TARJETA", "TRANSFERENCIA"];
    return Object.keys(totales.porMetodo).sort((a, b) => {
      const idxA = orden.indexOf(a);
      const idxB = orden.indexOf(b);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a.localeCompare(b);
    });
  }, [totales]);

  if (!turno) return null;

  return (
    <Modal
      abierto={turno !== null}
      titulo={`Movimientos del turno #${turno.id} — ${turno.abierto_por}`}
      alCerrar={alCerrar}
      ancho="sm:max-w-2xl"
    >
      <div className="p-4 sm:p-5">
        {error && <Alert tono="peligro">{error}</Alert>}
        {!datos && !error && <PageSpinner texto="Cargando movimientos…" />}
        {datos && totales && (
          <div className="space-y-6">
            {/* Resumen por tipo de pago (Minicards) */}
            <section>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Resumen de ingresos del turno
              </h4>
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                {/* Total Neto Card */}
                <div className="flex items-center gap-2.5 rounded-xl border border-zinc-800 bg-zinc-900 p-2.5 text-white shadow-sm">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-800 text-emerald-400">
                    <DollarSign className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="block truncate text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                      Total Neto
                    </span>
                    <span className="block truncate text-sm font-bold tabular-nums text-white">
                      S/ {totales.totalNeto.toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Minicards por cada tipo de pago */}
                {metodosKeys.map((metodo) => {
                  const monto = totales.porMetodo[metodo];
                  const info = infoEstiloMetodo(metodo);
                  const IconoComponente = info.icono;
                  return (
                    <div
                      key={metodo}
                      className={`flex items-center gap-2.5 rounded-xl border p-2.5 transition-colors ${info.claseCard}`}
                    >
                      <div
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${info.claseIcono}`}
                      >
                        <IconoComponente className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="block truncate text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                          {info.etiqueta}
                        </span>
                        <span className={`block truncate text-sm font-bold tabular-nums ${info.claseMonto}`}>
                          S/ {monto.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

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
      </div>
    </Modal>
  );
}

