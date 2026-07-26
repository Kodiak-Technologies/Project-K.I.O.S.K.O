// Modal de confirmación genérico. Reutilizable para "Aprobar", "Rechazar",
// "Activar/Desactivar", "Registrar pago", etc.
import type { ReactNode } from "react";
import { Modal } from "../../../shared/components/ui";

interface Props {
  abierto: boolean;
  titulo: string;
  /** Contenido principal del modal (texto de advertencia + opcional children). */
  mensaje?: ReactNode;
  /** Texto del botón principal. Default "Confirmar". */
  textoConfirmar?: string;
  /** Variante del botón principal. Default "primario". */
  variante?: "primario" | "peligro";
  cargando?: boolean;
  alCancelar: () => void;
  alConfirmar: () => void;
  children?: ReactNode;
}

export function ModalConfirmacion({
  abierto,
  titulo,
  mensaje,
  textoConfirmar = "Confirmar",
  variante = "primario",
  cargando,
  alCancelar,
  alConfirmar,
  children,
}: Props) {
  return (
    <Modal
      abierto={abierto}
      titulo={titulo}
      alCerrar={alCancelar}
      pie={
        <>
          <button
            type="button"
            onClick={alCancelar}
            disabled={cargando}
            className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={alConfirmar}
            disabled={cargando}
            className={`inline-flex min-h-tactil items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-60 ${
              variante === "peligro"
                ? "bg-peligro hover:bg-red-700"
                : "bg-marca hover:opacity-85"
            }`}
          >
            {textoConfirmar}
          </button>
        </>
      }
    >
      {mensaje && <p className="text-sm text-zinc-700">{mensaje}</p>}
      {children}
    </Modal>
  );
}
