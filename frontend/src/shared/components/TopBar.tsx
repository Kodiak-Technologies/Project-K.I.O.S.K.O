// Barra superior: hamburguesa (abre el sidebar en pantallas chicas), campanita
// con las notificaciones NO leídas y cierre de sesión. La página de
// Notificaciones del sidebar muestra el historial completo (leídas incluidas);
// la campanita es solo el "entrante". Personalización de colores: Configuración.
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bell, LogOut, Menu } from "lucide-react";
// Import cruzado consciente: las notificaciones son del módulo D, igual que el
// POS consume el catálogo del módulo B a través de su puerto.
import { useNotificaciones } from "../../modules/modulo-d-documentos/hooks/useNotificaciones";
import { notificacionesHttpAdapter } from "../../modules/modulo-d-documentos/services/notificaciones.http-adapter";
import { useAuthContext } from "../lib/auth-context";

function CampanaNotificaciones() {
  const { notificaciones, noDisponible, recargar, marcarLeida } = useNotificaciones();
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);
  const ubicacion = useLocation();

  const noLeidas = notificaciones.filter((n) => !n.leida);

  // Cerrar al hacer clic fuera o al navegar.
  useEffect(() => {
    if (!abierto) return;
    const manejar = (e: MouseEvent) => {
      if (!contenedor.current?.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", manejar);
    return () => document.removeEventListener("mousedown", manejar);
  }, [abierto]);
  useEffect(() => setAbierto(false), [ubicacion.pathname]);

  // Auto-marcar todas como leídas al abrir la campana.
  useEffect(() => {
    if (abierto && noLeidas.length > 0) {
      void notificacionesHttpAdapter.marcarTodasLeidas().then(() => void recargar());
    }
  }, [abierto]);

  function alternar() {
    setAbierto((prev) => !prev);
  }

  return (
    <div className="relative" ref={contenedor}>
      <button
        onClick={alternar}
        title="Notificaciones"
        aria-label={`Notificaciones${noLeidas.length > 0 ? ` (${noLeidas.length} sin leer)` : ""}`}
        className="relative flex min-h-tactil min-w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
      >
        <Bell className="h-5 w-5" aria-hidden />
        {noLeidas.length > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-peligro px-1 text-[10px] font-semibold leading-none text-white">
            {noLeidas.length > 9 ? "9+" : noLeidas.length}
          </span>
        )}
      </button>

      {abierto && (
        <div className="absolute right-0 z-20 mt-2 w-80 max-w-[90vw] rounded-xl border border-zinc-200 bg-white shadow-lg">
          <header className="border-b border-zinc-100 px-4 py-2.5">
            <p className="text-sm font-semibold text-zinc-900">Notificaciones nuevas</p>
          </header>

          {noDisponible || noLeidas.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-zinc-500">
              {noDisponible ? "El módulo de notificaciones aún no está conectado." : "Nada nuevo por ahora."}
            </p>
          ) : (
            <ul className="max-h-80 divide-y divide-zinc-100 overflow-y-auto">
              {noLeidas.slice(0, 6).map((n) => (
                <li key={n.id} className="flex items-start gap-2 px-4 py-2.5">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-info-intenso" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-800">{n.titulo}</p>
                    <p className="line-clamp-2 text-xs text-zinc-500">{n.mensaje}</p>
                    {n.created_at && (
                      <p className="mt-0.5 text-[11px] text-zinc-400">
                        {new Date(n.created_at).toLocaleString("es-PE")}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => void marcarLeida(n.id)}
                    className="shrink-0 rounded px-1.5 py-1 text-xs text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
                  >
                    Leída
                  </button>
                </li>
              ))}
            </ul>
          )}

          <footer className="border-t border-zinc-100 px-4 py-2">
            <Link
              to="/notificaciones"
              className="block text-center text-sm font-medium text-marca hover:underline"
            >
              Ver todas las notificaciones
            </Link>
          </footer>
        </div>
      )}
    </div>
  );
}

export function TopBar({ alAbrirMenu }: { alAbrirMenu: () => void }) {
  const { usuario, logout } = useAuthContext();

  return (
    // h-16 fija, la misma del header del sidebar: los bordes quedan al ras.
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-2 border-b border-zinc-200 bg-white px-3 sm:px-4">
      <button
        onClick={alAbrirMenu}
        aria-label="Abrir menú"
        className="flex min-h-tactil min-w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 lg:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden />
      </button>

      <div className="flex-1" />

      <div className="flex items-center gap-1 sm:gap-2">
        <CampanaNotificaciones />
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
