// Router raíz: monta las rutas de cada módulo dentro del Layout autenticado.
// Los módulos B, C y D agregan sus rutas igual que rutasModuloA.
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import { rutasModuloA } from "./modules/modulo-a-seguridad/routes";
import Login from "./modules/modulo-a-seguridad/pages/Login";
import { Layout } from "./shared/components/Layout";
import { ProtectedRoute } from "./shared/components/ProtectedRoute";
import { AuthProvider } from "./shared/lib/auth-context";
import { TemaProvider } from "./shared/lib/theme-context";
import { useAuthContext } from "./shared/lib/auth-context";

function Inicio() {
  // El ADMIN aterriza en Usuarios; el CAJERO, de momento, en una bienvenida
  // (cuando existan los módulos B/C/D, irá al POS).
  const { usuario } = useAuthContext();
  if (usuario?.rol === "ADMIN") return <Navigate to="/usuarios" replace />;
  return (
    <p className="text-gray-600">
      Bienvenido, {usuario?.nombre}. Los módulos de ventas e inventario estarán disponibles pronto.
    </p>
  );
}

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
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
      // ...rutasModuloB, ...rutasModuloC, ...rutasModuloD
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return (
    <TemaProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </TemaProvider>
  );
}
