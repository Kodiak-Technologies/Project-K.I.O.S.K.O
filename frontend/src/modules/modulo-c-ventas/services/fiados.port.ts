// Puerto: interfaz de clientes, fiados (cuentas por cobrar) y abonos.
import type { AbonoFiado, Cliente, Fiado } from "../types";

export interface FiadosPort {
  listarClientes(q?: string): Promise<Cliente[]>;
  crearCliente(datos: { nombre: string; alias?: string; telefono?: string }): Promise<Cliente>;
  actualizarCliente(
    id: number,
    cambios: { nombre?: string; alias?: string; telefono?: string; activo?: boolean }
  ): Promise<Cliente>;
  /** Solo ADMIN: fija el tope de deuda del cliente (0 = sin límite). */
  fijarLimiteCredito(id: number, limite: number): Promise<Cliente>;
  listarFiados(clienteId?: number, pendientes?: boolean): Promise<Fiado[]>;
  abonosDeFiado(fiadoId: number): Promise<AbonoFiado[]>;
  registrarAbono(fiadoId: number, monto: number, metodo: string): Promise<Fiado>;
}
