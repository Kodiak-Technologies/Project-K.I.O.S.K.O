// Modal de selección de estilo de interfaz.
// Muestra las 3 paletas como tarjetas visuales con preview de colores.
import { createPortal } from "react-dom";
import { Check, X } from "lucide-react";
import { ESTILOS_UI, useEstiloUI, type EstiloId } from "../lib/estilo-context";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
}

export function ModalEstiloUI({ abierto, alCerrar }: Props) {
  const { estiloActivo, setEstilo } = useEstiloUI();

  function elegir(id: EstiloId) {
    setEstilo(id);
    alCerrar();
  }

  if (!abierto) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)" }}
      onClick={alCerrar}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Seleccionar estilo de interfaz"
        className="w-full max-w-lg overflow-hidden rounded-2xl shadow-2xl"
        style={{ background: "var(--ui-fondo-panel)", border: "1px solid var(--ui-borde)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabecera */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: "1px solid var(--ui-borde)" }}
        >
          <div>
            <h3
              className="text-base font-semibold"
              style={{ color: "var(--ui-texto-principal)" }}
            >
              Estilo de interfaz
            </h3>
            <p className="text-xs mt-0.5" style={{ color: "var(--ui-texto-secundario)" }}>
              Cambia la apariencia visual de fondos y paneles
            </p>
          </div>
          <button
            onClick={alCerrar}
            aria-label="Cerrar"
            className="rounded-lg p-2 transition-colors"
            style={{ color: "var(--ui-texto-secundario)" }}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tarjetas de estilos */}
        <div className="grid grid-cols-3 gap-3 p-5">
          {ESTILOS_UI.map((estilo) => {
            const activo = estiloActivo === estilo.id;
            return (
              <button
                key={estilo.id}
                onClick={() => elegir(estilo.id)}
                className="group relative flex flex-col items-center gap-3 rounded-xl p-3 transition-all duration-150"
                style={{
                  border: activo
                    ? "2px solid var(--color-primario)"
                    : "2px solid var(--ui-borde)",
                  background: activo ? "var(--ui-activo-bg)" : "var(--ui-fondo)",
                }}
                aria-pressed={activo}
                title={estilo.nombre}
              >
                {/* Preview visual de la paleta */}
                <div
                  className="relative h-16 w-full overflow-hidden rounded-lg"
                  style={{ background: estilo.previewFondo }}
                >
                  {/* Sidebar mini */}
                  <div
                    className="absolute inset-y-0 left-0 w-1/3 rounded-l-lg"
                    style={{ background: estilo.previewPanel }}
                  />
                  {/* Navbar mini */}
                  <div
                    className="absolute inset-x-0 top-0 h-1/4"
                    style={{ background: estilo.previewPanel, opacity: 0.85 }}
                  />
                  {/* Líneas decorativas */}
                  <div className="absolute inset-x-[34%] top-[30%] space-y-1.5 px-1">
                    <div className="h-1 w-3/4 rounded-full" style={{ background: estilo.previewAccent }} />
                    <div className="h-1 w-1/2 rounded-full" style={{ background: estilo.previewAccent }} />
                    <div className="h-1 w-2/3 rounded-full" style={{ background: estilo.previewAccent }} />
                  </div>
                  {/* Check de activo */}
                  {activo && (
                    <div
                      className="absolute bottom-1 right-1 flex h-5 w-5 items-center justify-center rounded-full"
                      style={{ background: "var(--color-primario)" }}
                    >
                      <Check className="h-3 w-3 text-white" />
                    </div>
                  )}
                </div>

                <span
                  className="text-xs font-medium"
                  style={{
                    color: activo ? "var(--color-primario)" : "var(--ui-texto-principal)",
                  }}
                >
                  {estilo.nombre}
                </span>
              </button>
            );
          })}
        </div>

        {/* Descripción del activo */}
        <div
          className="px-5 pb-5"
        >
          <p className="text-xs text-center" style={{ color: "var(--ui-texto-secundario)" }}>
            {ESTILOS_UI.find((e) => e.id === estiloActivo)?.descripcion}
          </p>
        </div>
      </div>
    </div>,
    document.body
  );
}
