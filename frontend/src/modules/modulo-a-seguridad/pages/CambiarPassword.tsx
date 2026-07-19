// Cambio de contraseña obligatorio: los usuarios nuevos (o con contraseña
// reseteada) llegan acá tras el login y no pueden usar el sistema hasta
// definir una contraseña propia. ProtectedRoute fuerza la redirección.
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { KeyRound } from "lucide-react";
import { Alert, Button, Input } from "../../../shared/components/ui";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { authHttpAdapter } from "../services/auth.http-adapter";

// Misma política que al crear usuarios (y que valida el backend).
const esquemaPassword = z
  .object({
    actual: z.string().min(1, "Ingresa tu contraseña actual (la temporal que te dieron)"),
    nueva: z
      .string()
      .min(8, "La nueva contraseña debe tener al menos 8 caracteres")
      .regex(/[A-Za-z]/, "La nueva contraseña debe incluir una letra")
      .regex(/\d/, "La nueva contraseña debe incluir un número"),
    confirmacion: z.string(),
  })
  .refine((datos) => datos.nueva === datos.confirmacion, {
    message: "La confirmación no coincide con la nueva contraseña",
    path: ["confirmacion"],
  })
  .refine((datos) => datos.nueva !== datos.actual, {
    message: "La nueva contraseña no puede ser igual a la temporal",
    path: ["nueva"],
  });

export default function CambiarPassword() {
  const { usuario, actualizarUsuario, logout } = useAuthContext();
  const navegar = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);

    const validacion = esquemaPassword.safeParse({ actual, nueva, confirmacion });
    if (!validacion.success) {
      setError(validacion.error.errors[0].message);
      return;
    }

    setEnviando(true);
    try {
      await authHttpAdapter.cambiarPassword(actual, nueva);
      // La bandera ya quedó en false en el backend; reflejarlo en memoria
      // desbloquea el resto de rutas sin re-loguear.
      actualizarUsuario({ debe_cambiar_password: false });
      navegar("/", { replace: true });
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4">
      <div className="w-full max-w-sm">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-tarjeta sm:p-8">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-marca text-white">
              <KeyRound className="h-7 w-7" aria-hidden />
            </span>
            <h1 className="text-xl font-semibold text-zinc-900">Crea tu contraseña</h1>
            <p className="mt-0.5 text-sm text-zinc-500">
              Hola, {usuario?.nombre}. Tu contraseña actual es temporal: elige una propia para
              empezar a usar el sistema.
            </p>
          </div>

          <form onSubmit={(e) => void manejarEnvio(e)} className="space-y-4">
            <Input
              label="Contraseña temporal"
              requerido
              type="password"
              autoComplete="current-password"
              value={actual}
              onChange={(e) => setActual(e.target.value)}
            />
            <Input
              label="Nueva contraseña"
              requerido
              type="password"
              autoComplete="new-password"
              placeholder="Mín. 8 caracteres, letra y número"
              value={nueva}
              onChange={(e) => setNueva(e.target.value)}
            />
            <Input
              label="Confirmar nueva contraseña"
              requerido
              type="password"
              autoComplete="new-password"
              value={confirmacion}
              onChange={(e) => setConfirmacion(e.target.value)}
            />

            {error && <Alert tono="peligro">{error}</Alert>}

            <Button type="submit" cargando={enviando} className="w-full">
              {enviando ? "Guardando…" : "Guardar y continuar"}
            </Button>
          </form>
        </div>
        <button
          onClick={() => void logout()}
          className="mt-4 block w-full text-center text-xs text-zinc-400 hover:text-zinc-600 hover:underline"
        >
          Salir y volver al inicio de sesión
        </button>
      </div>
    </div>
  );
}
