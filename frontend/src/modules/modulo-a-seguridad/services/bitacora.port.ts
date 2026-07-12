// Puerto: consulta de la bitácora de auditoría (solo lectura, por diseño es inmutable).
import type { BitacoraPaginada, FiltrosBitacora } from "../types";

export interface BitacoraPort {
  consultar(filtros: FiltrosBitacora): Promise<BitacoraPaginada>;
}
