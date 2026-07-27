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
    <div className="min-h-screen w-full max-w-full overflow-x-clip bg-zinc-50">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 lg:block">
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

      <div className="w-full min-w-0 overflow-x-clip lg:pl-64">
        <TopBar alAbrirMenu={() => setMenuAbierto(true)} />
        <main className="mx-auto w-full min-w-0 max-w-6xl p-3 sm:p-6 pb-20">
          <Outlet />
        </main>
      </div>

      <AcercaDelSistema />
    </div>
  );
}
