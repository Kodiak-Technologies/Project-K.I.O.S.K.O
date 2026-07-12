// Página de gestión de usuarios (solo ADMIN): crear, desactivar/reactivar,
// eliminar (borrado lógico) y resetear contraseña.
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useAuth } from "../hooks/useAuth";
import { useUsuarios } from "../hooks/useUsuarios";

const esquemaNuevoUsuario = z.object({
  username: z
    .string()
    .regex(/^[a-z0-9_]{3,30}$/, "Usuario: 3-30 caracteres, solo minúsculas, números o guion bajo"),
  nombre: z.string().min(1, "Ingresa el nombre para mostrar"),
  password: z
    .string()
    .min(8, "La contraseña debe tener al menos 8 caracteres")
    .regex(/[A-Za-z]/, "La contraseña debe incluir una letra")
    .regex(/\d/, "La contraseña debe incluir un número"),
  rol_id: z.number(),
});

export default function GestionUsuarios() {
  const { usuario: usuarioActual } = useAuth();
  const { usuarios, roles, cargando, error, crear, cambiarEstado, eliminar, resetearPassword } =
    useUsuarios();

  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const [nuevo, setNuevo] = useState({ username: "", nombre: "", password: "", rol_id: 2 });

  async function manejarCrear(evento: FormEvent) {
    evento.preventDefault();
    setErrorAccion(null);
    const validacion = esquemaNuevoUsuario.safeParse(nuevo);
    if (!validacion.success) {
      setErrorAccion(validacion.error.errors[0].message);
      return;
    }
    try {
      await crear({ ...nuevo, forzar_cambio_password: true });
      setMensaje(`Usuario '${nuevo.username}' creado. Deberá cambiar su contraseña al ingresar.`);
      setNuevo({ username: "", nombre: "", password: "", rol_id: 2 });
      setMostrarFormulario(false);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
  }

  async function manejarResetPassword(id: number, username: string) {
    const nueva = window.prompt(`Nueva contraseña para '${username}' (mín. 8, letra y número):`);
    if (!nueva) return;
    setErrorAccion(null);
    try {
      await resetearPassword(id, nueva, true);
      setMensaje(`Contraseña de '${username}' reseteada. Deberá cambiarla al ingresar.`);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
  }

  async function manejarEliminar(id: number, username: string) {
    if (!window.confirm(`¿Eliminar al usuario '${username}'? Su historial se conserva (borrado lógico).`))
      return;
    setErrorAccion(null);
    try {
      await eliminar(id);
      setMensaje(`Usuario '${username}' eliminado (lógicamente).`);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
  }

  if (cargando) return <p className="text-gray-500">Cargando usuarios…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Gestión de usuarios</h2>
        <button
          onClick={() => setMostrarFormulario(!mostrarFormulario)}
          className="rounded-lg px-3 py-1.5 text-sm font-medium text-white"
          style={{ backgroundColor: "var(--color-primario)" }}
        >
          {mostrarFormulario ? "Cancelar" : "+ Nuevo usuario"}
        </button>
      </div>

      {mensaje && <p className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-700">{mensaje}</p>}
      {errorAccion && <p className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{errorAccion}</p>}

      {mostrarFormulario && (
        <form onSubmit={manejarCrear} className="mb-6 grid gap-3 rounded-lg border bg-white p-4 sm:grid-cols-2">
          <input
            className="rounded border px-3 py-2 text-sm"
            placeholder="Usuario (ej. vendedor1)"
            value={nuevo.username}
            onChange={(e) => setNuevo({ ...nuevo, username: e.target.value })}
          />
          <input
            className="rounded border px-3 py-2 text-sm"
            placeholder="Nombre para mostrar (ej. Vendedor 1)"
            value={nuevo.nombre}
            onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })}
          />
          <input
            className="rounded border px-3 py-2 text-sm"
            type="password"
            placeholder="Contraseña inicial"
            value={nuevo.password}
            onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })}
          />
          <select
            className="rounded border px-3 py-2 text-sm"
            value={nuevo.rol_id}
            onChange={(e) => setNuevo({ ...nuevo, rol_id: Number(e.target.value) })}
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nombre}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 sm:col-span-2">
            El usuario deberá cambiar esta contraseña en su primer ingreso.
          </p>
          <button
            type="submit"
            className="rounded-lg px-4 py-2 text-sm font-medium text-white sm:col-span-2"
            style={{ backgroundColor: "var(--color-primario)" }}
          >
            Crear usuario
          </button>
        </form>
      )}

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-600">
            <tr>
              <th className="px-3 py-2">Usuario</th>
              <th className="px-3 py-2">Nombre</th>
              <th className="px-3 py-2">Rol</th>
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2">Último acceso</th>
              <th className="px-3 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="px-3 py-2 font-mono">{u.username}</td>
                <td className="px-3 py-2">{u.nombre}</td>
                <td className="px-3 py-2">{u.rol}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      u.activo ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {u.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-3 py-2 text-gray-500">
                  {u.ultimo_acceso ? new Date(u.ultimo_acceso).toLocaleString("es-PE") : "—"}
                </td>
                <td className="space-x-2 whitespace-nowrap px-3 py-2">
                  {u.id !== usuarioActual?.id && (
                    <>
                      <button
                        onClick={() => void cambiarEstado(u.id, !u.activo)}
                        className="text-blue-600 hover:underline"
                      >
                        {u.activo ? "Desactivar" : "Reactivar"}
                      </button>
                      <button
                        onClick={() => void manejarResetPassword(u.id, u.username)}
                        className="text-amber-600 hover:underline"
                      >
                        Reset clave
                      </button>
                      <button
                        onClick={() => void manejarEliminar(u.id, u.username)}
                        className="text-red-600 hover:underline"
                      >
                        Eliminar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
