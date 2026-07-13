// Página de inicio de sesión. REGLA DE NEGOCIO: no existe "Crear cuenta" —
// solo el ADMIN crea usuarios desde Gestión de Usuarios. Los usernames son
// siempre en minúsculas (misma regla que al crearlos), por eso el toLowerCase.
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { Store } from "lucide-react";
import { Alert } from "../../../shared/components/ui";
import { Button } from "../../../shared/components/ui";
import { Input } from "../../../shared/components/ui";
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
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4">
      <div className="w-full max-w-sm">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-tarjeta sm:p-8">
          <div className="mb-6 text-center">
            {tema.logoUrl ? (
              <img
                src={tema.logoUrl}
                alt="Logo"
                className="mx-auto mb-3 h-14 w-14 rounded-xl object-contain"
              />
            ) : (
              <span className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-900 text-white">
                <Store className="h-7 w-7" aria-hidden />
              </span>
            )}
            <h1 className="text-xl font-semibold text-zinc-900">{tema.nombreNegocio}</h1>
            <p className="mt-0.5 text-sm text-zinc-500">Inicia sesión para continuar</p>
          </div>

          <form onSubmit={manejarEnvio} className="space-y-4">
            <Input
              label="Usuario"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ej. vendedor1"
            />
            <Input
              label="Contraseña"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            {error && <Alert tono="peligro">{error}</Alert>}

            <Button type="submit" cargando={enviando} className="w-full">
              {enviando ? "Ingresando…" : "Ingresar"}
            </Button>
          </form>
          {/* Sin enlace de registro: las cuentas las crea únicamente el ADMIN. */}
        </div>
        <p className="mt-4 text-center text-xs text-zinc-400">
          ¿Olvidaste tu contraseña? Pídele al administrador que la resetee.
        </p>
      </div>
    </div>
  );
}
