// Contexto global de sesión: usuario actual, login y logout.
// Al montar la app intenta recuperar la sesión con el token guardado (sesión persistente).
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { authHttpAdapter } from "../../modules/modulo-a-seguridad/services/auth.http-adapter";
import type { Usuario } from "../../modules/modulo-a-seguridad/types";
import { registrarLogoutForzado, tokenStorage } from "./http-client";

interface AuthContextValue {
  usuario: Usuario | null;
  cargando: boolean;
  login: (username: string, password: string) => Promise<Usuario>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  // Recuperar sesión al abrir la app (la dueña no quiere loguearse cada vez).
  useEffect(() => {
    registrarLogoutForzado(() => setUsuario(null));
    if (!tokenStorage.obtenerAccess()) {
      setCargando(false);
      return;
    }
    authHttpAdapter
      .me()
      .then(setUsuario)
      .catch(() => tokenStorage.limpiar())
      .finally(() => setCargando(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const respuesta = await authHttpAdapter.login(username, password);
    tokenStorage.guardar(respuesta.access_token, respuesta.refresh_token);
    setUsuario(respuesta.usuario);
    return respuesta.usuario;
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokenStorage.obtenerRefresh();
    if (refresh) {
      try {
        await authHttpAdapter.logout(refresh);
      } catch {
        // Si el backend no responde igual cerramos la sesión local.
      }
    }
    tokenStorage.limpiar();
    setUsuario(null);
  }, []);

  return (
    <AuthContext.Provider value={{ usuario, cargando, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuthContext debe usarse dentro de <AuthProvider>");
  return contexto;
}
