// Modal de confirmación genérico. Reutilizable para "Aprobar", "Rechazar",
// "Activar/Desactivar", "Registrar pago", etc.
import type { ReactNode } from "react";
import { Button, Modal } from "../../../shared/components/ui";

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
          <Button type="button" variante="secundario" onClick={alCancelar} disabled={cargando}>
            Cancelar
          </Button>
          {/* `cargando` pinta el spinner del Button: sin él, una aprobación
              lenta no daba ninguna señal y parecía que el clic no había
              entrado (la usuaria volvía a apretar). */}
          <Button type="button" variante={variante} onClick={alConfirmar} cargando={cargando}>
            {cargando ? "Procesando…" : textoConfirmar}
          </Button>
        </>
      }
    >
      {mensaje && <p className="text-sm text-zinc-700">{mensaje}</p>}
      {children}
    </Modal>
  );
}
