// Cierre de caja (HU-C07, RF-17): el sistema SUGIERE el efectivo esperado
// (inicial + ventas en efectivo − devoluciones) y el cajero registra lo que
// contó. Lo vendido por Yape/tarjeta se muestra aparte: ese dinero existe
// pero NO está físicamente en el cajón. Si el contado difiere de la sugerencia,
// el comentario es obligatorio y la administradora lo ve en su panel.
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Banknote, Lock, Smartphone } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
} from "../../../shared/components/ui";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { cajaHttpAdapter } from "../services/caja.http-adapter";
import { useCaja } from "../hooks/useCaja";
import type { ResumenCaja } from "../types";

export default function CierreCaja() {
  const { turno, cargando, error, noDisponible, cerrar } = useCaja();
  const navegar = useNavigate();
  const [resumen, setResumen] = useState<ResumenCaja | null>(null);
  const [montoFinal, setMontoFinal] = useState("");
  const [comentario, setComentario] = useState("");
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  // La sugerencia se carga al entrar; el monto contado se prellena con ella.
  useEffect(() => {
    if (turno?.estado !== "ABIERTO") return;
    cajaHttpAdapter
      .resumen()
      .then((r) => {
        setResumen(r);
        setMontoFinal(r.efectivo_esperado.toFixed(2));
      })
      .catch((e) => {
        if (!servicioNoDisponible(e)) setErrorAccion(mensajeDeError(e));
      });
  }, [turno?.estado]);

  const monto = Number(montoFinal);
  const diferencia =
    resumen && montoFinal !== "" && !Number.isNaN(monto)
      ? Math.round((monto - resumen.efectivo_esperado) * 100) / 100
      : null;
  const requiereComentario = diferencia !== null && diferencia !== 0;

  async function manejarCerrar(evento: FormEvent) {
    evento.preventDefault();
    if (Number.isNaN(monto) || monto < 0) {
      setErrorAccion("Ingresa el efectivo contado (0 o más).");
      return;
    }
    if (requiereComentario && !comentario.trim()) {
      setErrorAccion("El monto difiere de la sugerencia: explica el motivo en el comentario.");
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      await cerrar(monto, comentario.trim() || undefined);
      navegar("/caja");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Cierre de caja" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Consultando la caja…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  if (turno?.estado !== "ABIERTO") {
    return (
      <div className="max-w-xl">
        <PageHeader titulo="Cierre de caja" />
        <Alert tono="info">No hay un turno abierto. Abre la caja primero.</Alert>
      </div>
    );
  }

  const digitales = resumen
    ? Object.entries(resumen.totales_por_metodo).filter(([codigo]) => codigo !== "EFECTIVO")
    : [];

  return (
    <div>
      <PageHeader
        titulo="Cierre de caja"
        descripcion={`Turno abierto por ${turno.abierto_por} el ${new Date(turno.abierto_en).toLocaleString("es-PE")}.`}
      />

      {!resumen ? (
        <PageSpinner texto="Calculando la sugerencia de cierre…" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Columna izquierda: qué debería haber y qué se vendió */}
          <div className="space-y-4">
            <Card titulo="Efectivo esperado en caja" descripcion="La sugerencia del sistema: solo dinero físico.">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-zinc-500">Apertura del turno</dt>
                  <dd className="tabular-nums">S/ {resumen.desglose.monto_inicial.toFixed(2)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-zinc-500">+ Ventas en efectivo</dt>
                  <dd className="tabular-nums">S/ {resumen.desglose.ventas_efectivo.toFixed(2)}</dd>
                </div>
                {resumen.desglose.devoluciones_efectivo > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-zinc-500">− Devoluciones en efectivo</dt>
                    <dd className="tabular-nums text-red-700">
                      − S/ {resumen.desglose.devoluciones_efectivo.toFixed(2)}
                    </dd>
                  </div>
                )}
                <div className="flex items-center justify-between border-t border-zinc-100 pt-2">
                  <dt className="flex items-center gap-1.5 font-medium text-zinc-800">
                    <Banknote className="h-4 w-4" aria-hidden /> Debe haber en el cajón
                  </dt>
                  <dd className="text-xl font-semibold tabular-nums text-zinc-900">
                    S/ {resumen.efectivo_esperado.toFixed(2)}
                  </dd>
                </div>
              </dl>
            </Card>

            <Card
              titulo="Cobrado por medios digitales"
              descripcion="Este dinero es parte de lo vendido, pero NO está físicamente en la caja."
            >
              {digitales.length === 0 ? (
                <p className="text-sm text-zinc-500">Ninguna venta digital en este turno.</p>
              ) : (
                <dl className="space-y-2 text-sm">
                  {digitales.map(([codigo, monto]) => (
                    <div key={codigo} className="flex justify-between">
                      <dt className="flex items-center gap-1.5 text-zinc-500">
                        <Smartphone className="h-4 w-4" aria-hidden /> {codigo}
                      </dt>
                      <dd className="tabular-nums">S/ {monto.toFixed(2)}</dd>
                    </div>
                  ))}
                </dl>
              )}
              <div className="mt-3 flex items-center justify-between border-t border-zinc-100 pt-2 text-sm">
                <span className="text-zinc-500">
                  Total vendido del turno ({resumen.numero_ventas} ventas)
                </span>
                <span className="font-semibold tabular-nums text-zinc-900">
                  S/ {resumen.total_vendido.toFixed(2)}
                </span>
              </div>
            </Card>
          </div>

          {/* Columna derecha: el conteo real y el cierre */}
          <Card titulo="Cerrar turno" descripcion="Cuenta el efectivo físico del cajón y regístralo.">
            <form onSubmit={(e) => void manejarCerrar(e)} className="space-y-4">
              <Input
                label="Efectivo contado (S/)"
                requerido
                type="number"
                step="0.10"
                min={0}
                inputMode="decimal"
                value={montoFinal}
                onChange={(e) => setMontoFinal(e.target.value)}
              />

              {diferencia !== null && (
                <div
                  className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-sm ${
                    diferencia === 0
                      ? "bg-exito-suave text-green-800"
                      : "bg-alerta-suave text-yellow-800"
                  }`}
                >
                  <span>
                    {diferencia === 0
                      ? "La caja cuadra con la sugerencia"
                      : diferencia > 0
                        ? "Sobrante contra lo esperado"
                        : "Faltante contra lo esperado"}
                  </span>
                  <span className="font-semibold tabular-nums">
                    {diferencia > 0 ? "+" : ""}S/ {diferencia.toFixed(2)}
                  </span>
                </div>
              )}

              {requiereComentario && (
                <Input
                  label="Comentario (obligatorio por la diferencia)"
                  requerido
                  placeholder="ej. billete falso retirado, gasto de caja chica…"
                  value={comentario}
                  onChange={(e) => setComentario(e.target.value)}
                />
              )}
              <p className="text-xs text-zinc-500">
                El cierre queda registrado con tu nombre y no se puede eliminar. Si registras un
                monto distinto al sugerido, la administradora verá la diferencia y tu comentario
                en el historial de turnos.
              </p>
              {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
              <Button
                type="submit"
                variante="peligro"
                cargando={procesando}
                icono={<Lock className="h-4 w-4" aria-hidden />}
              >
                Cerrar caja
              </Button>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
