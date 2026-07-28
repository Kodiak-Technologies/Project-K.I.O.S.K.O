import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AcercaDelSistema } from "./AcercaDelSistema";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function Layout() {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const ubicacion = useLocation();

  useEffect(() => setMenuAbierto(false), [ubicacion.pathname]);

  return (
    // Shell de alto fijo (h-full): sidebar + columna de contenido. El único que
    // scrollea es <main>; todo lo demás está clipeado para que ni el menú ni la
    // barra superior se corran, y para que no aparezca una segunda barra
    // vertical al borde de la pantalla.
    <div className="flex h-full w-full max-w-full overflow-hidden bg-zinc-50">
      <aside className="hidden w-64 shrink-0 lg:block">
        <Sidebar />
      </aside>

      {menuAbierto && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-zinc-900/40" onClick={() => setMenuAbierto(false)} aria-hidden />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] shadow-xl">
            <Sidebar />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col overflow-x-clip">
        <TopBar alAbrirMenu={() => setMenuAbierto(true)} />
        <main className="relative z-20 min-h-0 flex-1 overflow-y-auto overflow-x-clip">
          {/* pb-14: deja libre la esquina donde flota el botón "Acerca del sistema". */}
          <div className="mx-auto h-full w-full min-w-0 max-w-6xl p-3 pb-14 sm:p-6 sm:pb-14">
            <Outlet />
          </div>
        </main>
      </div>

      <AcercaDelSistema />
    </div>
  );
}
