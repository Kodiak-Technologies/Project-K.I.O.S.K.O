// Botón "Instalar app": instala la web como aplicación (con su ícono, a pantalla
// completa y sin la barra del navegador). Donde el navegador lo permite, abre su
// diálogo "Instalar"; en iPhone y otros casos muestra los pasos. Se oculta solo
// cuando ya se está usando como app.
import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import { Compass, Download, EllipsisVertical, Globe, Share, SquarePlus } from "lucide-react";
import { useInstalarApp, instalarApp, type SistemaOperativo } from "../lib/pwa";
import { Button, Modal } from "./ui";

const PASOS: Record<SistemaOperativo, [LucideIcon, string][]> = {
  ios: [
    [Compass, "Abre esta página en Safari."],
    [Share, "Toca el botón Compartir (el cuadro con la flecha hacia arriba)."],
    [SquarePlus, "Elige \"Agregar a inicio\" y toca \"Agregar\"."],
  ],
  android: [
    [Globe, "Abre esta página en Chrome."],
    [EllipsisVertical, "Toca el menú ⋮ arriba a la derecha."],
    [Download, "Elige \"Instalar app\" o \"Agregar a pantalla de inicio\"."],
  ],
  otro: [
    [Globe, "Abre esta página en Chrome o Edge."],
    [Download, "Toca el ícono de instalar en la barra de direcciones."],
  ],
};

export function BotonInstalarApp({ className = "" }: { className?: string }) {
  const app = useInstalarApp();
  const [ayuda, setAyuda] = useState(false);
  if (!app.visible) return null;

  async function tocar() {
    if (!(await instalarApp())) setAyuda(true);
  }

  return (
    <>
      <Button
        type="button"
        variante="secundario"
        icono={<Download className="h-4 w-4" aria-hidden />}
        className={className}
        onClick={() => void tocar()}
      >
        Instalar app
      </Button>
      <Modal
        abierto={ayuda}
        titulo="Instalar en tu dispositivo"
        alCerrar={() => setAyuda(false)}
        pie={<Button onClick={() => setAyuda(false)}>Entendido</Button>}
      >
        <div className="space-y-4">
          <p className="text-sm text-zinc-500">
            Queda con su ícono en tu pantalla de inicio, se abre a pantalla completa y se actualiza sola.
          </p>
          <ol className="space-y-3">
            {PASOS[app.sistema].map(([Icono, texto], i) => (
              <li key={i} className="flex items-center gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-zinc-700">
                  <Icono className="h-4 w-4" aria-hidden />
                </span>
                <span className="text-sm text-zinc-800">
                  {i + 1}. {texto}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </Modal>
    </>
  );
}
