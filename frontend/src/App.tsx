// Router raíz: monta las rutas de cada módulo dentro del Layout autenticado.
import { Link, Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { ArrowRight, Package, ScrollText, ShoppingCart, Users, Wallet } from "lucide-react";
import { rutasModuloA } from "./modules/modulo-a-seguridad/routes";
import { rutasModuloB } from "./modules/modulo-b-inventario/routes";
import { rutasModuloC } from "./modules/modulo-c-ventas/routes";
import { rutasModuloD } from "./modules/modulo-d-documentos/routes";
import CambiarPassword from "./modules/modulo-a-seguridad/pages/CambiarPassword";
import Login from "./modules/modulo-a-seguridad/pages/Login";
import { Layout } from "./shared/components/Layout";
import { ProtectedRoute } from "./shared/components/ProtectedRoute";
import { Card, PageHeader } from "./shared/components/ui";
import { Alert } from "./shared/components/ui/Feedback";
import { Button } from "./shared/components/ui/Button";
import { AuthProvider } from "./shared/lib/auth-context";
import { TemaProvider } from "./shared/lib/theme-context";
import { EstiloProvider } from "./shared/lib/estilo-context";
import { useAuthContext } from "./shared/lib/auth-context";
import { useEffect, useState } from "react";
import { httpClient } from "./shared/lib/http-client";
import { AlertTriangle, ExternalLink } from "lucide-react";

function AccesoRapido({ a, titulo, detalle, icono: Icono }: { a: string; titulo: string; detalle: string; icono: LucideIcon }) {
  return (
    <Link to={a} className="group">
      <Card className="h-full transition-colors group-hover:border-zinc-400">
        <div className="flex items-start justify-between">
          {/* El color secundario de la dueña pinta estos íconos (default: gris). */}
          <div className="rounded-lg bg-zinc-100 p-2.5">
            <Icono className="h-5 w-5 text-marca-secundario" aria-hidden />
          </div>
          <ArrowRight className="h-4 w-4 text-zinc-300 transition-transform group-hover:translate-x-0.5 group-hover:text-zinc-500" aria-hidden />
        </div>
        <p className="mt-3 font-medium text-zinc-900">{titulo}</p>
        <p className="mt-0.5 text-sm text-zinc-500">{detalle}</p>
      </Card>
    </Link>
  );
}

interface DriveStatus {
  autorizado: boolean;
  conectado: boolean;
  expirado: boolean;
  tiene_refresh_token: boolean;
  puede_reconectar: boolean;
  token_expiry: string | null;
  mensaje: string | null;
}

function Inicio() {
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";
  const [driveStatus, setDriveStatus] = useState<DriveStatus | null>(null);
  const [loadingDrive, setLoadingDrive] = useState(false);

  const fetchDriveStatus = async () => {
    if (!esAdmin) return;
    try {
      setLoadingDrive(true);
      const { data } = await httpClient.get<DriveStatus>("/drive/status");
      setDriveStatus(data);
    } catch (error) {
      console.error("Error al obtener estado de Google Drive:", error);
    } finally {
      setLoadingDrive(false);
    }
  };

  const handleConectarDrive = async () => {
    try {
      const { data } = await httpClient.get<{ auth_url: string }>("/drive/auth-url");
      window.open(data.auth_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      console.error("Error al obtener URL de autorización de Google Drive:", error);
    }
  };

  useEffect(() => {
    fetchDriveStatus();
    const interval = setInterval(fetchDriveStatus, 30000);
    return () => clearInterval(interval);
  }, [esAdmin]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("drive") === "ok" || params.get("drive") === "error") {
      setTimeout(fetchDriveStatus, 500);
    }
  }, [esAdmin]);

  const driveNoConectado = esAdmin && driveStatus !== null && !driveStatus.conectado;

  return (
    <div>
      {driveNoConectado && (
        <Alert tono="alerta">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between w-full">
            <span>Google Drive no está conectado.</span>
            <Button
              onClick={handleConectarDrive}
              disabled={loadingDrive}
              className="w-full sm:w-auto"
              compacto
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Conectar a Google Drive
            </Button>
          </div>
        </Alert>
      )}
      <PageHeader
        titulo={`Hola, ${usuario?.nombre ?? ""}`}
        descripcion="¿Qué necesitas hacer hoy?"
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AccesoRapido a="/pos" titulo="Punto de venta" detalle="Registrar una venta" icono={ShoppingCart} />
        <AccesoRapido a="/caja" titulo="Caja" detalle="Abrir o cerrar el turno" icono={Wallet} />
        <AccesoRapido a="/catalogo" titulo="Catálogo" detalle="Consultar stock y precios" icono={Package} />
        {esAdmin && (
          <>
            <AccesoRapido a="/usuarios" titulo="Usuarios" detalle="Cuentas del personal" icono={Users} />
            <AccesoRapido a="/bitacora" titulo="Bitácora" detalle="Quién hizo qué y cuándo" icono={ScrollText} />
          </>
        )}
      </div>
    </div>
  );
}

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    // Fuera del Layout: mientras la contraseña sea temporal no hay sidebar ni
    // ninguna otra pantalla (ProtectedRoute redirige siempre acá).
    path: "/cambiar-password",
    element: (
      <ProtectedRoute>
        <CambiarPassword />
      </ProtectedRoute>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Inicio /> },
      ...rutasModuloA,
      ...rutasModuloB,
      ...rutasModuloC,
      ...rutasModuloD,
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return (
    <EstiloProvider>
      <TemaProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </TemaProvider>
    </EstiloProvider>
  );
}
