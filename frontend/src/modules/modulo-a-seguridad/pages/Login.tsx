// Página de inicio de sesión. REGLA DE NEGOCIO: no existe "Crear cuenta" —
// solo el ADMIN crea usuarios desde Gestión de Usuarios.
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useTema } from "../../../shared/lib/theme-context";
import { useAuth } from "../hooks/useAuth";

const esquemaLogin = z.object({
  username: z.string().min(1, "Ingresa tu usuario"),
  password: z.string().min(1, "Ingresa tu contraseña"),
});

export default function Login() {
  const { login } = useAuth();
  const { tema, sincronizarDesdeBackend } = useTema();
  const navegar = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);

    const validacion = esquemaLogin.safeParse({ username, password });
    if (!validacion.success) {
      setError(validacion.error.errors[0].message);
      return;
    }

    setEnviando(true);
    try {
      await login(username.trim().toLowerCase(), password);
      await sincronizarDesdeBackend(); // trae logo/colores del negocio ya con sesión
      navegar("/", { replace: true });
    } catch (e) {
      setError(mensajeDeError(e)); // "Usuario o contraseña incorrectos." — genérico a propósito
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-xl border bg-white p-6 shadow-sm">
        <div className="mb-6 text-center">
          {tema.logoUrl && (
            <img src={tema.logoUrl} alt="Logo" className="mx-auto mb-2 h-16 w-16 rounded object-contain" />
          )}
          <h1 className="text-xl font-semibold" style={{ color: "var(--color-primario)" }}>
            {tema.nombreNegocio}
          </h1>
          <p className="text-sm text-gray-500">Inicia sesión para continuar</p>
        </div>

        <form onSubmit={manejarEnvio} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Usuario</label>
            <input
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2"
              placeholder="ej. vendedor1"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Contraseña</label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg px-4 py-2 font-medium text-white disabled:opacity-60"
            style={{ backgroundColor: "var(--color-primario)" }}
          >
            {enviando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
        {/* Sin enlace de registro: las cuentas las crea únicamente el ADMIN. */}
      </div>
    </div>
  );
}
