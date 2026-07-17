// Hook: fiados (cuentas por cobrar) y clientes.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { fiadosHttpAdapter } from "../services/fiados.http-adapter";
import type { Cliente, Fiado } from "../types";

export function useFiados(soloPendientes = true) {
  const [fiados, setFiados] = useState<Fiado[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async () => {
    setError(null);
    try {
      const [listaFiados, listaClientes] = await Promise.all([
        fiadosHttpAdapter.listarFiados(undefined, soloPendientes),
        fiadosHttpAdapter.listarClientes(),
      ]);
      setFiados(listaFiados);
      setClientes(listaClientes);
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, [soloPendientes]);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const crearCliente = useCallback(
    async (datos: { nombre: string; alias?: string; telefono?: string }) => {
      const creado = await fiadosHttpAdapter.crearCliente(datos);
      await recargar();
      return creado;
    },
    [recargar]
  );

  const fijarLimite = useCallback(
    async (clienteId: number, limite: number) => {
      await fiadosHttpAdapter.fijarLimiteCredito(clienteId, limite);
      await recargar();
    },
    [recargar]
  );

  const abonar = useCallback(
    async (fiadoId: number, monto: number, metodo: string) => {
      const fiado = await fiadosHttpAdapter.registrarAbono(fiadoId, monto, metodo);
      await recargar();
      return fiado;
    },
    [recargar]
  );

  return { fiados, clientes, cargando, error, noDisponible, recargar, crearCliente, fijarLimite, abonar };
}
