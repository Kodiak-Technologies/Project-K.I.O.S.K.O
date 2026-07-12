// Barra superior: logo + nombre del negocio, controles de paleta/tipografía
// (la clienta los pidió AQUÍ, no escondidos en configuración) y cierre de sesión.
import { useState } from "react";
import { useAuthContext } from "../lib/auth-context";
import { useTema } from "../lib/theme-context";

const TIPOGRAFIAS = ["Inter", "Roboto", "Poppins", "Lato", "Montserrat", "system-ui"];

export function TopBar() {
  const { usuario, logout } = useAuthContext();
  const { tema, aplicarTema } = useTema();
  const [mostrarTema, setMostrarTema] = useState(false);

  return (
    <header
      className="flex items-center justify-between gap-2 px-3 py-2 text-white shadow"
      style={{ backgroundColor: "var(--color-primario)" }}
    >
      <div className="flex min-w-0 items-center gap-2">
        {tema.logoUrl && (
          <img src={tema.logoUrl} alt="Logo" className="h-8 w-8 rounded bg-white object-contain p-0.5" />
        )}
        <span className="truncate text-lg font-semibold">{tema.nombreNegocio}</span>
      </div>

      <div className="flex items-center gap-2">
        {/* Controles de tema en la barra superior (pedido explícito de la clienta) */}
        <div className="relative">
          <button
            onClick={() => setMostrarTema(!mostrarTema)}
            className="rounded px-2 py-1 text-sm hover:bg-white/20"
            title="Personalizar colores y tipografía"
          >
            🎨
          </button>
          {mostrarTema && (
            <div className="absolute right-0 z-20 mt-2 w-64 rounded-lg border bg-white p-3 text-gray-800 shadow-lg">
              <label className="mb-2 flex items-center justify-between text-sm">
                Color primario
                <input
                  type="color"
                  value={tema.colorPrimario}
                  onChange={(e) => aplicarTema({ colorPrimario: e.target.value })}
                />
              </label>
              <label className="mb-2 flex items-center justify-between text-sm">
                Color secundario
                <input
                  type="color"
                  value={tema.colorSecundario}
                  onChange={(e) => aplicarTema({ colorSecundario: e.target.value })}
                />
              </label>
              <label className="flex items-center justify-between gap-2 text-sm">
                Tipografía
                <select
                  className="rounded border px-1 py-0.5"
                  value={tema.tipografia}
                  onChange={(e) => aplicarTema({ tipografia: e.target.value })}
                >
                  {TIPOGRAFIAS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <p className="mt-2 text-xs text-gray-500">
                El ADMIN puede guardar estos valores para todos en Configuración.
              </p>
            </div>
          )}
        </div>

        {usuario && (
          <>
            <span className="hidden text-sm sm:inline">
              {usuario.nombre} <span className="opacity-75">({usuario.rol})</span>
            </span>
            <button
              onClick={() => void logout()}
              className="rounded bg-white/20 px-2 py-1 text-sm hover:bg-white/30"
            >
              Salir
            </button>
          </>
        )}
      </div>
    </header>
  );
}
