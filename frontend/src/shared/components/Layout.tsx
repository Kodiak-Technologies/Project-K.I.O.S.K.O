// Layout autenticado: barra superior + navegación (responsive desde 360 px) + contenido.
import { NavLink, Outlet } from "react-router-dom";
import { useAuthContext } from "../lib/auth-context";
import { TopBar } from "./TopBar";

const enlaces = [
  { a: "/usuarios", texto: "Usuarios", soloAdmin: true },
  { a: "/bitacora", texto: "Bitácora", soloAdmin: true },
  { a: "/configuracion", texto: "Configuración", soloAdmin: true },
  // Los módulos B, C y D agregan aquí sus enlaces cuando monten sus rutas.
];

export function Layout() {
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";

  return (
    <div className="min-h-screen bg-gray-50">
      <TopBar />
      <nav className="flex gap-1 overflow-x-auto border-b bg-white px-2 py-1">
        {enlaces
          .filter((e) => !e.soloAdmin || esAdmin)
          .map((e) => (
            <NavLink
              key={e.a}
              to={e.a}
              className={({ isActive }) =>
                `whitespace-nowrap rounded px-3 py-1.5 text-sm ${
                  isActive ? "text-white" : "text-gray-700 hover:bg-gray-100"
                }`
              }
              style={({ isActive }) =>
                isActive ? { backgroundColor: "var(--color-primario)" } : undefined
              }
            >
              {e.texto}
            </NavLink>
          ))}
      </nav>
      <main className="mx-auto max-w-5xl p-3 sm:p-6">
        <Outlet />
      </main>
    </div>
  );
}
