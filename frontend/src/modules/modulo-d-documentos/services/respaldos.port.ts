import type { Respaldo } from "../types";

export interface RespaldosPort {
  listar(): Promise<Respaldo[]>;
  crear(): Promise<Respaldo>;
  descargar(id: number): Promise<Blob>;
  restaurar(id: number): Promise<void>;
}
