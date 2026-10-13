// Puerto: cuentas de fiado (clientes, pagos y créditos).
import type { ClienteFiado, EstadoCuentaFiado, MovimientoFiado } from "../types";

export interface DatosClienteFiado {
  nombre?: string;
  telefono?: string | null;
  nota?: string | null;
  /** Solo ADMIN. */
  limite_mensual?: number;
  /** Solo ADMIN. */
  activo?: boolean;
}

export interface FiadosPort {
  listar(buscar?: string, incluirInactivos?: boolean): Promise<ClienteFiado[]>;
  crear(datos: DatosClienteFiado & { nombre: string }): Promise<ClienteFiado>;
  estadoDeCuenta(clienteId: number): Promise<EstadoCuentaFiado>;
  actualizar(clienteId: number, cambios: DatosClienteFiado): Promise<ClienteFiado>;
  /** El cliente paga lo que debe: entra a la caja del turno actual. */
  pagar(clienteId: number, monto: number, metodo: string, nota?: string): Promise<MovimientoFiado>;
  /** Crédito ya pagado (solo ADMIN): queda a favor y entra a la caja del turno. */
  creditoPagado(clienteId: number, monto: number, metodo: string, nota?: string): Promise<MovimientoFiado>;
}
