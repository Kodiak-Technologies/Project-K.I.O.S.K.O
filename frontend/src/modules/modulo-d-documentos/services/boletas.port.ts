// Puerto: interfaz de consulta/descarga de boletas.
import type { Boleta } from "../types";

export interface BoletasPort {
  listar(desde?: string, hasta?: string): Promise<Boleta[]>;
}
