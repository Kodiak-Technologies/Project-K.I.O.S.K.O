// Hook: listar, crear, editar proveedores y gestionar deuda (compras a crédito / pagos).
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { proveedoresHttpAdapter } from "../services/proveedores.http-adapter";
import type {
  EdicionProveedor,
  FiltrosPagosProveedor,
  FiltrosProveedores,
  NuevoPagoProveedor,
  NuevoProveedor,
  PagosPaginadosResponse,
  PaginadosResponse,
  PagoProveedor,
  Proveedor,
} from "../types";

interface EstadoHook {
  proveedores: Proveedor[];
  paginados: PaginadosResponse<Proveedor> | null;
  cargando: boolean;
  error: string | null;
  noDisponible: boolean;
  recargar: (filtros?: FiltrosProveedores) => Promise<void>;
  obtener: (id: number) => Promise<Proveedor>;
  crear: (datos: NuevoProveedor) => Promise<Proveedor>;
  editar: (id: number, datos: EdicionProveedor) => Promise<Proveedor>;
  registrarCompraCredito: (id: number, datos: NuevoPagoProveedor) => Promise<PagoProveedor>;
  registrarPago: (id: number, datos: NuevoPagoProveedor) => Promise<PagoProveedor>;
  listarPagos: (proveedorId: number, filtros?: FiltrosPagosProveedor) => Promise<PagosPaginadosResponse>;
}

export function useProveedores(filtrosIniciales?: FiltrosProveedores): EstadoHook {
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [paginados, setPaginados] = useState<PaginadosResponse<Proveedor> | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (filtros?: FiltrosProveedores) => {
    setError(null);
    try {
      const resp = await proveedoresHttpAdapter.listar(filtros);
      setPaginados(resp);
      setProveedores(resp.items);
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar(filtrosIniciales);
  }, [recargar, filtrosIniciales]);

  const crear = useCallback(
    async (datos: NuevoProveedor) => {
      const creado = await proveedoresHttpAdapter.crear(datos);
      await recargar(filtrosIniciales);
      return creado;
    },
    [recargar, filtrosIniciales]
  );

  const editar = useCallback(
    async (id: number, datos: EdicionProveedor) => {
      const actualizado = await proveedoresHttpAdapter.editar(id, datos);
      await recargar(filtrosIniciales);
      return actualizado;
    },
    [recargar, filtrosIniciales]
  );

  const registrarCompraCredito = useCallback(
    async (id: number, datos: NuevoPagoProveedor) => {
      const pago = await proveedoresHttpAdapter.registrarCompraCredito(id, datos);
      await recargar(filtrosIniciales);
      return pago;
    },
    [recargar, filtrosIniciales]
  );

  const registrarPago = useCallback(
    async (id: number, datos: NuevoPagoProveedor) => {
      const pago = await proveedoresHttpAdapter.registrarPago(id, datos);
      await recargar(filtrosIniciales);
      return pago;
    },
    [recargar, filtrosIniciales]
  );

  const listarPagos = useCallback(
    (proveedorId: number, filtros?: FiltrosPagosProveedor) =>
      proveedoresHttpAdapter.listarPagos(proveedorId, filtros),
    []
  );

  const obtener = useCallback((id: number) => proveedoresHttpAdapter.obtener(id), []);

  return {
    proveedores,
    paginados,
    cargando,
    error,
    noDisponible,
    recargar,
    obtener,
    crear,
    editar,
    registrarCompraCredito,
    registrarPago,
    listarPagos,
  };
}
