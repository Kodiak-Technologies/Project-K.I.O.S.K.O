// Página de gestión de usuarios (solo ADMIN): crear, desactivar/reactivar,
// eliminar (borrado lógico) y resetear contraseña.
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { KeyRound, Trash2, UserPlus, Users } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  PageHeader,
  PageSpinner,
  Select,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useAuth } from "../hooks/useAuth";
import { useUsuarios } from "../hooks/useUsuarios";
import type { Usuario } from "../types";

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

const FORMULARIO_VACIO = { username: "", nombre: "", password: "", rol_id: 2 };

export default function GestionUsuarios() {
  const { usuario: usuarioActual } = useAuth();
  const { usuarios, roles, cargando, error, crear, cambiarEstado, eliminar, resetearPassword } =
    useUsuarios();

  const [modalCrear, setModalCrear] = useState(false);
  const [nuevo, setNuevo] = useState(FORMULARIO_VACIO);
  const [paraResetear, setParaResetear] = useState<Usuario | null>(null);
  const [nuevaPassword, setNuevaPassword] = useState("");
  const [paraEliminar, setParaEliminar] = useState<Usuario | null>(null);

  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  function cerrarModales() {
    setModalCrear(false);
    setParaResetear(null);
    setParaEliminar(null);
    setNuevaPassword("");
    setErrorAccion(null);
  }

  async function ejecutar(accion: () => Promise<void>, exito: string) {
    setErrorAccion(null);
    setMensaje(null);
    setProcesando(true);
    try {
      await accion();
      setMensaje(exito);
      cerrarModales();
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  async function manejarCrear(evento: FormEvent) {
    evento.preventDefault();
    const validacion = esquemaNuevoUsuario.safeParse(nuevo);
    if (!validacion.success) {
      setErrorAccion(validacion.error.errors[0].message);
      return;
    }
    await ejecutar(async () => {
      await crear({ ...nuevo, forzar_cambio_password: true });
      setNuevo(FORMULARIO_VACIO);
    }, `Usuario '${nuevo.username}' creado. Deberá cambiar su contraseña al ingresar.`);
  }

  if (cargando) return <PageSpinner texto="Cargando usuarios…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const columnas: Columna<Usuario>[] = [
    { titulo: "Usuario", render: (u) => <span className="font-mono text-zinc-800">{u.username}</span> },
    { titulo: "Nombre", render: (u) => u.nombre },
    { titulo: "Rol", render: (u) => <Badge tono={u.rol === "ADMIN" ? "info" : "neutro"}>{u.rol}</Badge> },
    {
      titulo: "Estado",
      render: (u) => <Badge tono={u.activo ? "exito" : "neutro"}>{u.activo ? "Activo" : "Inactivo"}</Badge>,
    },
    {
      titulo: "Último acceso",
      soloEscritorio: true,
      render: (u) => (
        <span className="text-zinc-500">
          {u.ultimo_acceso ? new Date(u.ultimo_acceso).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Acciones",
      render: (u) =>
        u.id === usuarioActual?.id ? (
          <span className="text-xs text-zinc-400">(tú)</span>
        ) : (
          <div className="flex items-center gap-1">
            <Button
              variante="secundario"
              compacto
              onClick={() =>
                void ejecutar(
                  () => cambiarEstado(u.id, !u.activo),
                  `Usuario '${u.username}' ${u.activo ? "desactivado" : "reactivado"}.`
                )
              }
            >
              {u.activo ? "Desactivar" : "Reactivar"}
            </Button>
            <Button
              variante="fantasma"
              compacto
              title="Resetear contraseña"
              aria-label={`Resetear contraseña de ${u.username}`}
              onClick={() => setParaResetear(u)}
              icono={<KeyRound className="h-4 w-4" aria-hidden />}
            />
            <Button
              variante="fantasma"
              compacto
              title="Eliminar"
              aria-label={`Eliminar a ${u.username}`}
              className="text-peligro hover:bg-peligro-suave"
              onClick={() => setParaEliminar(u)}
              icono={<Trash2 className="h-4 w-4" aria-hidden />}
            />
          </div>
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Gestión de usuarios"
        descripcion="Cuentas del personal: solo el ADMIN puede crearlas o modificarlas."
        acciones={
          <Button onClick={() => setModalCrear(true)} icono={<UserPlus className="h-4 w-4" aria-hidden />}>
            Nuevo usuario
          </Button>
        }
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}
      {errorAccion && !modalCrear && !paraResetear && !paraEliminar && (
        <div className="mb-4">
          <Alert tono="peligro">{errorAccion}</Alert>
        </div>
      )}

      <Card sinPadding>
        <Table
          columnas={columnas}
          filas={usuarios}
          claveDe={(u) => u.id}
          vacio={<EmptyState icono={Users} titulo="Sin usuarios" descripcion="Crea la primera cuenta del personal." />}
        />
      </Card>

      {/* Crear usuario */}
      <Modal abierto={modalCrear} titulo="Nuevo usuario" alCerrar={cerrarModales}>
        <form onSubmit={(e) => void manejarCrear(e)} className="space-y-4">
          <Input
            label="Usuario"
            requerido
            placeholder="ej. vendedor1"
            autoCapitalize="none"
            value={nuevo.username}
            onChange={(e) => setNuevo({ ...nuevo, username: e.target.value })}
          />
          <Input
            label="Nombre para mostrar"
            requerido
            placeholder="ej. Vendedor 1"
            value={nuevo.nombre}
            onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })}
          />
          <Input
            label="Contraseña inicial"
            requerido
            type="password"
            placeholder="Mín. 8 caracteres, letra y número"
            value={nuevo.password}
            onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })}
          />
          <Select
            label="Rol"
            value={nuevo.rol_id}
            onChange={(e) => setNuevo({ ...nuevo, rol_id: Number(e.target.value) })}
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nombre}
              </option>
            ))}
          </Select>
          <p className="text-xs text-zinc-500">El usuario deberá cambiar esta contraseña en su primer ingreso.</p>
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
          <div className="flex justify-end gap-2">
            <Button type="button" variante="secundario" onClick={cerrarModales}>
              Cancelar
            </Button>
            <Button type="submit" cargando={procesando}>
              Crear usuario
            </Button>
          </div>
        </form>
      </Modal>

      {/* Resetear contraseña */}
      <Modal
        abierto={paraResetear !== null}
        titulo={`Resetear contraseña de '${paraResetear?.username}'`}
        alCerrar={cerrarModales}
        pie={
          <>
            <Button variante="secundario" onClick={cerrarModales}>
              Cancelar
            </Button>
            <Button
              cargando={procesando}
              onClick={() =>
                paraResetear &&
                void ejecutar(
                  () => resetearPassword(paraResetear.id, nuevaPassword, true),
                  `Contraseña de '${paraResetear.username}' reseteada. Deberá cambiarla al ingresar.`
                )
              }
            >
              Resetear
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Nueva contraseña"
            requerido
            type="password"
            placeholder="Mín. 8 caracteres, letra y número"
            value={nuevaPassword}
            onChange={(e) => setNuevaPassword(e.target.value)}
          />
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
        </div>
      </Modal>

      {/* Confirmar eliminación */}
      <Modal
        abierto={paraEliminar !== null}
        titulo="Eliminar usuario"
        alCerrar={cerrarModales}
        pie={
          <>
            <Button variante="secundario" onClick={cerrarModales}>
              Cancelar
            </Button>
            <Button
              variante="peligro"
              cargando={procesando}
              onClick={() =>
                paraEliminar &&
                void ejecutar(() => eliminar(paraEliminar.id), `Usuario '${paraEliminar.username}' eliminado (lógicamente).`)
              }
            >
              Eliminar
            </Button>
          </>
        }
      >
        <p className="text-sm text-zinc-600">
          ¿Eliminar al usuario <strong>'{paraEliminar?.username}'</strong>? Su historial se conserva
          (borrado lógico).
        </p>
        {errorAccion && (
          <div className="mt-3">
            <Alert tono="peligro">{errorAccion}</Alert>
          </div>
        )}
      </Modal>
    </div>
  );
}
