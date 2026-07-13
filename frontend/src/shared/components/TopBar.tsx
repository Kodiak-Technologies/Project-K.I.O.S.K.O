// Barra superior: hamburguesa (abre el sidebar en pantallas chicas), controles
// de paleta/tipografía (la clienta los pidió AQUÍ, no escondidos en configuración)
// y cierre de sesión. Superficie blanca: el color de marca vive en los acentos.
import { useEffect, useRef, useState } from "react";
import { LogOut, Menu, Palette } from "lucide-react";
import { useAuthContext } from "../lib/auth-context";
import { useTema } from "../lib/theme-context";

const TIPOGRAFIAS = ["Inter", "Roboto", "Poppins", "Lato", "Montserrat", "system-ui"];

function ControlesDeTema() {
  const { tema, aplicarTema } = useTema();
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);

  // Cerrar al hacer clic fuera del popover.
  useEffect(() => {
    if (!abierto) return;
    const manejar = (e: MouseEvent) => {
      if (!contenedor.current?.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", manejar);
    return () => document.removeEventListener("mousedown", manejar);
  }, [abierto]);

  return (
    <div className="relative" ref={contenedor}>
      <button
        onClick={() => setAbierto(!abierto)}
        title="Personalizar colores y tipografía"
        aria-label="Personalizar colores y tipografía"
        className="flex min-h-tactil min-w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
      >
        <Palette className="h-5 w-5" aria-hidden />
      </button>
      {abierto && (
        <div className="absolute right-0 z-20 mt-2 w-64 rounded-xl border border-zinc-200 bg-white p-3 shadow-lg">
          <label className="mb-2 flex items-center justify-between text-sm text-zinc-700">
            Color primario
            <input
              type="color"
              value={tema.colorPrimario}
              onChange={(e) => aplicarTema({ colorPrimario: e.target.value })}
            />
          </label>
          <label className="mb-2 flex items-center justify-between text-sm text-zinc-700">
            Color secundario
            <input
              type="color"
              value={tema.colorSecundario}
              onChange={(e) => aplicarTema({ colorSecundario: e.target.value })}
            />
          </label>
          <label className="flex items-center justify-between gap-2 text-sm text-zinc-700">
            Tipografía
            <select
              className="rounded-lg border border-zinc-300 px-2 py-1 text-sm"
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
          <p className="mt-2 text-xs text-zinc-500">
            El ADMIN puede guardar estos valores para todos en Configuración.
          </p>
        </div>
      )}
    </div>
  );
}

export function TopBar({ alAbrirMenu }: { alAbrirMenu: () => void }) {
  const { usuario, logout } = useAuthContext();

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-zinc-200 bg-white px-3 py-2 sm:px-4">
      <button
        onClick={alAbrirMenu}
        aria-label="Abrir menú"
        className="flex min-h-tactil min-w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 lg:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden />
      </button>

      <div className="flex-1" />

      <div className="flex items-center gap-1 sm:gap-2">
        <ControlesDeTema />
        {usuario && (
          <>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight text-zinc-800">{usuario.nombre}</p>
              <p className="text-xs leading-tight text-zinc-400">{usuario.rol}</p>
            </div>
            <button
              onClick={() => void logout()}
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
              className="flex min-h-tactil min-w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
            >
              <LogOut className="h-5 w-5" aria-hidden />
            </button>
          </>
        )}
      </div>
    </header>
  );
}
