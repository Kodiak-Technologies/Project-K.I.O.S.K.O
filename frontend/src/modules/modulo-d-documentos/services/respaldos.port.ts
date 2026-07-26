import type { Respaldo, RespaldosPaginados } from "../types";

export interface RespaldosPort {
  listar(page?: number, pageSize?: number): Promise<RespaldosPaginados>;
  crear(): Promise<Respaldo>;
  descargar(id: number): Promise<Blob>;
  restaurar(id: number): Promise<void>;
}
