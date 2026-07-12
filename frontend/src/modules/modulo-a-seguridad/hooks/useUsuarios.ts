// Hook: estado y acciones de gestión de usuarios (consume el puerto, no axios directo).
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { usuariosHttpAdapter } from "../services/usuarios.http-adapter";
import type { CrearUsuarioInput } from "../services/usuarios.port";
import type { Rol, Usuario } from "../types";

export function useUsuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [roles, setRoles] = useState<Rol[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [listaUsuarios, listaRoles] = await Promise.all([
        usuariosHttpAdapter.listar(),
        usuariosHttpAdapter.listarRoles(),
      ]);
      setUsuarios(listaUsuarios);
      setRoles(listaRoles);
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const crear = useCallback(
    async (datos: CrearUsuarioInput) => {
      await usuariosHttpAdapter.crear(datos);
      await recargar();
    },
    [recargar]
  );

  const cambiarEstado = useCallback(
    async (id: number, activo: boolean) => {
      await usuariosHttpAdapter.cambiarEstado(id, activo);
      await recargar();
    },
    [recargar]
  );

  const eliminar = useCallback(
    async (id: number, motivo?: string) => {
      await usuariosHttpAdapter.eliminar(id, motivo);
      await recargar();
    },
    [recargar]
  );

  const resetearPassword = useCallback(
    async (id: number, passwordNueva: string, forzarCambio: boolean) => {
      await usuariosHttpAdapter.resetearPassword(id, passwordNueva, forzarCambio);
    },
    []
  );

  return { usuarios, roles, cargando, error, recargar, crear, cambiarEstado, eliminar, resetearPassword };
}
