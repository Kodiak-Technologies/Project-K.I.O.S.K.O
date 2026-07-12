// Hook del módulo: expone la sesión global con azúcar sintáctico propio del módulo.
import { useAuthContext } from "../../../shared/lib/auth-context";

export function useAuth() {
  const { usuario, cargando, login, logout } = useAuthContext();
  return {
    usuario,
    cargando,
    login,
    logout,
    esAdmin: usuario?.rol === "ADMIN",
    autenticado: usuario !== null,
  };
}
