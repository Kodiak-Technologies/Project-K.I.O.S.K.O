// Panel de navegación izquierdo. Agrupa enlaces por módulo, filtra por rol y
// ancla Configuración al fondo (decisión de diseño: config siempre abajo).
import { NavLink } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Bell,
  ClipboardCheck,
  History,
  Home,
  Package,
  PackagePlus,
  Receipt,
  ScrollText,
  Settings,
  ShoppingCart,
  Store,
  Truck,
  BarChart3,
  Users,
  Wallet,
} from "lucide-react";
import { useAuthContext } from "../lib/auth-context";
import { useTema } from "../lib/theme-context";

interface Enlace {
  a: string;
  texto: string;
  icono: LucideIcon;
  soloAdmin?: boolean;
}

interface Grupo {
  titulo?: string;
  enlaces: Enlace[];
}

// Los módulos B, C y D ya tienen acá su navegación; solo montan sus rutas.
const GRUPOS: Grupo[] = [
  { enlaces: [{ a: "/", texto: "Inicio", icono: Home }] },
  {
    titulo: "Ventas",
    enlaces: [
      { a: "/pos", texto: "Punto de venta", icono: ShoppingCart },
      { a: "/caja", texto: "Caja", icono: Wallet },
      { a: "/historial-ventas", texto: "Historial", icono: History },
    ],
  },
  {
    titulo: "Inventario",
    enlaces: [
      { a: "/catalogo", texto: "Catálogo", icono: Package },
      { a: "/productos", texto: "Productos", icono: PackagePlus, soloAdmin: true },
      { a: "/ingresos", texto: "Ingresos", icono: Truck },
      { a: "/aprobaciones", texto: "Aprobaciones", icono: ClipboardCheck, soloAdmin: true },
    ],
  },
  {
    titulo: "Documentos",
    enlaces: [
      { a: "/boletas", texto: "Boletas", icono: Receipt },
      { a: "/reportes", texto: "Reportes", icono: BarChart3, soloAdmin: true },
      { a: "/notificaciones", texto: "Notificaciones", icono: Bell },
    ],
  },
  {
    titulo: "Seguridad",
    enlaces: [
      { a: "/usuarios", texto: "Usuarios", icono: Users, soloAdmin: true },
      { a: "/bitacora", texto: "Bitácora", icono: ScrollText, soloAdmin: true },
    ],
  },
];

function Item({ enlace }: { enlace: Enlace }) {
  const Icono = enlace.icono;
  return (
    <NavLink
      to={enlace.a}
      end={enlace.a === "/"}
      className={({ isActive }) =>
        `relative flex min-h-tactil items-center gap-3 rounded-lg px-3 text-sm transition-colors ${
          isActive ? "bg-zinc-100 font-medium text-zinc-900" : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && <span className="absolute left-0 h-5 w-1 rounded-r bg-marca" aria-hidden />}
          <Icono className="h-5 w-5 shrink-0" aria-hidden />
          {enlace.texto}
        </>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  const { usuario } = useAuthContext();
  const { tema } = useTema();
  const esAdmin = usuario?.rol === "ADMIN";

  return (
    <div className="flex h-full flex-col border-r border-zinc-200 bg-white">
      {/* Identidad del negocio */}
      <div className="flex items-center gap-2.5 border-b border-zinc-100 px-4 py-4">
        {tema.logoUrl ? (
          <img src={tema.logoUrl} alt="Logo" className="h-9 w-9 rounded-lg object-contain" />
        ) : (
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 text-white">
            <Store className="h-5 w-5" aria-hidden />
          </span>
        )}
        <span className="truncate font-semibold text-zinc-900">{tema.nombreNegocio}</span>
      </div>

      {/* Navegación por módulos */}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {GRUPOS.map((grupo) => {
          const visibles = grupo.enlaces.filter((e) => !e.soloAdmin || esAdmin);
          if (visibles.length === 0) return null;
          return (
            <div key={grupo.titulo ?? "raiz"}>
              {grupo.titulo && (
                <p className="mb-1 px-3 text-xs font-medium uppercase tracking-wide text-zinc-400">
                  {grupo.titulo}
                </p>
              )}
              <div className="space-y-0.5">
                {visibles.map((e) => (
                  <Item key={e.a} enlace={e} />
                ))}
              </div>
            </div>
          );
        })}
      </nav>

      {/* Configuración SIEMPRE al fondo del panel */}
      {esAdmin && (
        <div className="border-t border-zinc-100 px-3 py-3">
          <Item enlace={{ a: "/configuracion", texto: "Configuración", icono: Settings }} />
        </div>
      )}
    </div>
  );
}
