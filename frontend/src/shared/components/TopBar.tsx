// Barra superior: hamburguesa (abre el sidebar en pantallas chicas), campanita
// con las notificaciones NO leídas, selector de estilo de interfaz y cierre de sesión.
// La página de Notificaciones del sidebar muestra el historial completo (leídas incluidas);
// la campanita es solo el "entrante". Personalización de colores: Configuración.
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bell, Check, CheckCheck, LogOut, Menu, Palette } from "lucide-react";
// Import cruzado consciente: las notificaciones son del módulo D, igual que el
// POS consume el catálogo del módulo B a través de su puerto.
import { useNotificaciones } from "../../modules/modulo-d-documentos/hooks/useNotificaciones";
import { notificacionesHttpAdapter } from "../../modules/modulo-d-documentos/services/notificaciones.http-adapter";
import { useAuthContext } from "../lib/auth-context";
import { ModalEstiloUI } from "./ModalEstiloUI";

function CampanaNotificaciones() {
  const { notificaciones, noDisponible, recargar, marcarLeida } = useNotificaciones();
  const [abierto, setAbierto] = useState(false);
  const [marcandoTodas, setMarcandoTodas] = useState(false);
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

  async function manejarMarcarTodasLeidas() {
    if (marcandoTodas || noLeidas.length === 0) return;
    setMarcandoTodas(true);
    try {
      await notificacionesHttpAdapter.marcarTodasLeidas();
      await recargar();
    } catch {
    } finally {
      setMarcandoTodas(false);
    }
  }

  function alternar() {
    setAbierto((prev) => !prev);
  }

  return (
    <div className="relative" ref={contenedor}>
      <button
        onClick={alternar}
        title="Notificaciones"
        aria-label={`Notificaciones${noLeidas.length > 0 ? ` (${noLeidas.length} sin leer)` : ""}`}
        className="relative flex min-h-tactil min-w-11 items-center justify-center rounded-lg transition-colors"
        style={{ color: "var(--ui-texto-secundario)" }}
      >
        <Bell className="h-5 w-5" aria-hidden />
        {noLeidas.length > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-peligro px-1 text-[10px] font-semibold leading-none text-white">
            {noLeidas.length > 9 ? "9+" : noLeidas.length}
          </span>
        )}
      </button>

      {abierto && (
        <div
          className="absolute right-0 z-20 mt-2 w-80 max-w-[90vw] rounded-xl shadow-lg"
          style={{ background: "var(--ui-fondo-panel)", border: "1px solid var(--ui-borde)" }}
        >
          <header className="flex items-center justify-between px-4 py-2.5" style={{ borderBottom: "1px solid var(--ui-separador)" }}>
            <p className="text-sm font-semibold" style={{ color: "var(--ui-texto-principal)" }}>
              Notificaciones
              {noLeidas.length > 0 && (
                <span className="ml-1.5 rounded-full bg-marca/10 px-2 py-0.5 text-xs font-semibold text-marca">
                  {noLeidas.length} nuevas
                </span>
              )}
            </p>
            {noLeidas.length > 0 && (
              <button
                type="button"
                onClick={manejarMarcarTodasLeidas}
                disabled={marcandoTodas}
                className="inline-flex items-center gap-1 text-xs font-medium text-marca hover:underline disabled:opacity-50"
                title="Marcar todas como leídas"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Marcar leídas
              </button>
            )}
          </header>

          {noDisponible || noLeidas.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm" style={{ color: "var(--ui-texto-secundario)" }}>
              {noDisponible ? "El módulo de notificaciones aún no está conectado." : "Nada nuevo por ahora."}
            </p>
          ) : (
            <ul className="max-h-80 divide-y overflow-y-auto" style={{ borderColor: "var(--ui-separador)" }}>
              {noLeidas.slice(0, 8).map((n) => (
                <li key={n.id} className="flex items-start gap-2 px-4 py-2.5 hover:bg-zinc-500/5 transition-colors">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-info-intenso" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium" style={{ color: "var(--ui-texto-principal)" }}>{n.titulo}</p>
                    <p className="line-clamp-2 text-xs" style={{ color: "var(--ui-texto-secundario)" }}>{n.mensaje}</p>
                    {n.created_at && (
                      <p className="mt-0.5 text-[11px]" style={{ color: "var(--ui-texto-secundario)" }}>
                        {new Date(n.created_at).toLocaleString("es-PE")}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => void marcarLeida(n.id)}
                    className="shrink-0 rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 transition-colors"
                    title="Marcar como leída"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <footer className="px-4 py-2" style={{ borderTop: "1px solid var(--ui-separador)" }}>
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
  const [modalEstilo, setModalEstilo] = useState(false);

  return (
    <header
      className="z-30 flex h-16 shrink-0 items-center justify-between gap-2 px-3 sm:px-4"
      style={{
        background: "var(--ui-fondo-panel)",
        borderBottom: "1px solid var(--ui-borde)",
      }}
    >
      <button
        onClick={alAbrirMenu}
        aria-label="Abrir menú"
        className="flex min-h-tactil min-w-11 items-center justify-center rounded-lg transition-colors lg:hidden"
        style={{ color: "var(--ui-texto-secundario)" }}
      >
        <Menu className="h-5 w-5" aria-hidden />
      </button>

      <div className="flex-1" />

      <div className="flex items-center gap-1 sm:gap-2">
        {/* Selector de estilo de interfaz */}
        <button
          onClick={() => setModalEstilo(true)}
          title="Cambiar estilo de interfaz"
          aria-label="Cambiar estilo de interfaz"
          className="relative flex min-h-tactil min-w-11 items-center justify-center rounded-lg transition-colors"
          style={{ color: "var(--ui-texto-secundario)" }}
        >
          <Palette className="h-5 w-5" aria-hidden />
        </button>

        <CampanaNotificaciones />

        {usuario && (
          <>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight" style={{ color: "var(--ui-texto-principal)" }}>{usuario.nombre}</p>
              <p className="text-xs leading-tight" style={{ color: "var(--ui-texto-secundario)" }}>{usuario.rol}</p>
            </div>
            <button
              onClick={() => void logout()}
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
              className="flex min-h-tactil min-w-11 items-center justify-center rounded-lg transition-colors"
              style={{ color: "var(--ui-texto-secundario)" }}
            >
              <LogOut className="h-5 w-5" aria-hidden />
            </button>
          </>
        )}
      </div>

      <ModalEstiloUI abierto={modalEstilo} alCerrar={() => setModalEstilo(false)} />
    </header>
  );
}
