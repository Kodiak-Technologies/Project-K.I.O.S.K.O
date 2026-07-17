// Modal de devolución parcial (HU-C08, RF-22): el cajero elige qué líneas y
// cuántas unidades vuelven. El backend repone stock, descuenta el efectivo de la
// caja actual y deja el rastro (quién, cuándo, motivo) para la administradora.
import { useEffect, useState } from "react";
import { Alert, Button, Input, Modal } from "../../../shared/components/ui";
import type { Venta } from "../types";

interface Props {
  venta: Venta | null;
  procesando: boolean;
  error: string | null;
  alCerrar: () => void;
  alConfirmar: (items: { detalle_id: number; cantidad: number }[], motivo: string) => void;
}

export function ModalDevolucion({ venta, procesando, error, alCerrar, alConfirmar }: Props) {
  const [cantidades, setCantidades] = useState<Record<number, string>>({});
  const [motivo, setMotivo] = useState("");

  useEffect(() => {
    setCantidades({});
    setMotivo("");
  }, [venta?.id]);

  if (!venta) return null;

  const lineas = venta.items
    .filter((i) => i.id !== undefined)
    .map((i) => ({ ...i, restante: i.cantidad - (i.cantidad_devuelta ?? 0) }))
    .filter((i) => i.restante > 0);

  const seleccion = lineas
    .map((linea) => ({ detalle_id: linea.id as number, cantidad: Number(cantidades[linea.id as number]) || 0, linea }))
    .filter((s) => s.cantidad > 0);
  const montoDevolucion = seleccion.reduce(
    (suma, s) => suma + s.cantidad * s.linea.precio_unitario,
    0
  );
  const valido =
    seleccion.length > 0 &&
    motivo.trim().length > 0 &&
    seleccion.every((s) => s.cantidad <= s.linea.restante);

  return (
    <Modal
      abierto={venta !== null}
      titulo={`Devolución de la venta #${venta.id}`}
      alCerrar={alCerrar}
      pie={
        <>
          <Button variante="secundario" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button
            variante="peligro"
            cargando={procesando}
            disabled={!valido}
            onClick={() =>
              alConfirmar(
                seleccion.map(({ detalle_id, cantidad }) => ({ detalle_id, cantidad })),
                motivo.trim()
              )
            }
          >
            Registrar devolución
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-zinc-600">
          Indica cuántas unidades vuelven de cada producto. El stock se repone y el dinero sale
          de la caja actual; todo queda registrado para la administradora.
        </p>
        <ul className="divide-y divide-zinc-100">
          {lineas.map((linea) => (
            <li key={linea.id} className="flex items-center gap-3 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-zinc-800">{linea.nombre}</p>
                <p className="text-xs text-zinc-500">
                  vendidas: {linea.cantidad}
                  {(linea.cantidad_devuelta ?? 0) > 0 && ` · ya devueltas: ${linea.cantidad_devuelta}`}
                  {" · "}S/ {linea.precio_unitario.toFixed(2)} c/u
                </p>
              </div>
              <input
                type="number"
                min={0}
                max={linea.restante}
                inputMode="numeric"
                aria-label={`Unidades a devolver de ${linea.nombre}`}
                placeholder="0"
                className="w-16 rounded-lg border border-zinc-300 px-2 py-1.5 text-center text-sm tabular-nums focus:border-zinc-500"
                value={cantidades[linea.id as number] ?? ""}
                onChange={(e) =>
                  setCantidades((actual) => ({ ...actual, [linea.id as number]: e.target.value }))
                }
              />
            </li>
          ))}
        </ul>
        {montoDevolucion > 0 && (
          <div className="flex items-center justify-between rounded-lg bg-zinc-50 px-3 py-2.5 text-sm">
            <span className="text-zinc-600">A devolver al cliente</span>
            <span className="font-semibold tabular-nums">S/ {montoDevolucion.toFixed(2)}</span>
          </div>
        )}
        <Input
          label="Motivo"
          requerido
          placeholder="ej. producto vencido, cliente cambió de opinión…"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        {error && <Alert tono="peligro">{error}</Alert>}
      </div>
    </Modal>
  );
}
