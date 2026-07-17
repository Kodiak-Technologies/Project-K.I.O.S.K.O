// Modal post-venta (HU-C05, RF-11): la venta YA está cerrada cuando esto se
// muestra — imprimir el ticket es opcional (solo si el cliente lo pide) y no
// bloquea seguir vendiendo. Muestra el vuelto en grande para entregar el cambio.
import { useState } from "react";
import { CheckCircle2, Printer } from "lucide-react";
import { Button, Modal, Select } from "../../../shared/components/ui";
import { useTema } from "../../../shared/lib/theme-context";
import {
  imprimirTicket,
  preferenciaPapel,
  type AnchoPapel,
} from "../services/ticket-printer";
import type { Venta } from "../types";

interface Props {
  venta: Venta | null;
  alCerrar: () => void;
}

export function ModalVentaRegistrada({ venta, alCerrar }: Props) {
  const { tema } = useTema();
  const [ancho, setAncho] = useState<AnchoPapel>(preferenciaPapel.obtener());

  if (!venta) return null;

  function imprimir() {
    if (!venta) return;
    imprimirTicket(venta, { nombre: tema.nombreNegocio, logoUrl: tema.logoUrl }, ancho);
  }

  return (
    <Modal
      abierto={venta !== null}
      titulo={`Venta #${venta.id} registrada`}
      alCerrar={alCerrar}
      pie={
        <>
          <Button
            variante="secundario"
            onClick={imprimir}
            icono={<Printer className="h-4 w-4" aria-hidden />}
          >
            Imprimir ticket
          </Button>
          <Button onClick={alCerrar}>Nueva venta</Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-green-700">
          <CheckCircle2 className="h-5 w-5" aria-hidden />
          <span className="text-sm font-medium">
            Cobrado S/ {venta.total.toFixed(2)} ({venta.metodo_pago})
          </span>
        </div>

        {venta.vuelto > 0 && (
          <div className="rounded-xl bg-zinc-900 px-4 py-3 text-center text-white">
            <p className="text-xs uppercase tracking-wide text-zinc-400">Vuelto a entregar</p>
            <p className="text-3xl font-bold tabular-nums">S/ {venta.vuelto.toFixed(2)}</p>
          </div>
        )}

        <div className="flex items-end gap-3">
          <div className="flex-1">
            <Select
              label="Papel de la impresora"
              value={ancho}
              onChange={(e) => {
                const valor = e.target.value as AnchoPapel;
                setAncho(valor);
                preferenciaPapel.guardar(valor);
              }}
            >
              <option value="80">Térmica 80 mm</option>
              <option value="58">Térmica 58 mm</option>
            </Select>
          </div>
        </div>
        <p className="text-xs text-zinc-500">
          El ticket es opcional: la venta ya quedó registrada y puedes seguir vendiendo sin
          imprimir. Compatible con cualquier impresora térmica instalada en el equipo.
        </p>
      </div>
    </Modal>
  );
}
