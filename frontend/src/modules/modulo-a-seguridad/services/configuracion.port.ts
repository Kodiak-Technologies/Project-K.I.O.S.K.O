// Puerto: lectura/edición de la configuración e identidad visual del negocio.
import type { Configuracion } from "../types";

export interface ConfiguracionPort {
  obtener(): Promise<Configuracion>;
  actualizar(cambios: Partial<Configuracion>): Promise<Configuracion>;
  subirLogo(archivo: File): Promise<Configuracion>;
}
