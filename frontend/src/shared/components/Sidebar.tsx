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
  PackageX,
  Receipt,
  ScrollText,
  Settings,
  ShoppingCart,
  Store,
  Truck,
  BarChart3,
  Database,
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
      { a: "/catalogo", texto: "Catálogo", icono: Package, soloAdmin: true },
      { a: "/ingresos", texto: "Ingresos", icono: Truck },
      { a: "/aprobaciones", texto: "Aprobaciones", icono: ClipboardCheck, soloAdmin: true },
      { a: "/proveedores", texto: "Proveedores", icono: Users, soloAdmin: true },
      { a: "/movimientos", texto: "Movimientos", icono: History },
    ],
  },
  {
    titulo: "Documentos",
    enlaces: [
      { a: "/notas-venta", texto: "Notas de Venta", icono: Receipt },
      { a: "/reportes", texto: "Reportes", icono: BarChart3, soloAdmin: true },
      { a: "/notificaciones", texto: "Notificaciones", icono: Bell },
      { a: "/respaldos", texto: "Respaldos", icono: Database, soloAdmin: true },
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
      className="relative flex min-h-tactil items-center gap-3 rounded-lg px-3 text-sm transition-colors"
      style={({ isActive }) => ({
        background: isActive ? "var(--ui-item-activo)" : "transparent",
        color: isActive ? "var(--ui-texto-principal)" : "var(--ui-texto-secundario)",
        fontWeight: isActive ? 500 : undefined,
      })}
    >
      {({ isActive }) => (
        <>
          {isActive && <span className="absolute left-0 h-5 w-1 rounded-r bg-marca" aria-hidden />}
          <Icono
            className="h-5 w-5 shrink-0"
            style={{ color: isActive ? "var(--color-primario)" : "var(--ui-texto-secundario)" }}
            aria-hidden
          />
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
    <div className="flex h-full flex-col" style={{ background: "var(--ui-fondo-panel)", borderRight: "1px solid var(--ui-borde)" }}>
      {/* Identidad del negocio. Altura FIJA h-16, igual que la TopBar: así los
          bordes inferiores quedan alineados sin importar el logo que suban. */}
      <div className="flex h-16 shrink-0 items-center gap-2.5 px-4" style={{ borderBottom: "1px solid var(--ui-borde)" }}>
        {tema.logoUrl ? (
          <img src={tema.logoUrl} alt="Logo" className="h-9 w-9 shrink-0 rounded-lg object-contain" />
        ) : (
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-marca text-white">
            <Store className="h-5 w-5" aria-hidden />
          </span>
        )}
        <span className="truncate font-semibold" style={{ color: "var(--ui-texto-principal)" }}>{tema.nombreNegocio}</span>
      </div>

      {/* Navegación por módulos */}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {GRUPOS.map((grupo) => {
          const visibles = grupo.enlaces.filter((e) => !e.soloAdmin || esAdmin);
          if (visibles.length === 0) return null;
          return (
            <div key={grupo.titulo ?? "raiz"}>
              {grupo.titulo && (
                <p className="mb-1 px-3 text-xs font-medium uppercase tracking-wide" style={{ color: "var(--ui-texto-secundario)" }}>
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
        <div className="px-3 py-3" style={{ borderTop: "1px solid var(--ui-borde)" }}>
          <Item enlace={{ a: "/configuracion", texto: "Configuración", icono: Settings }} />
        </div>
      )}
    </div>
  );
}
