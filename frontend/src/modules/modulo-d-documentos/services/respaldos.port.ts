import type { RespaldosPaginados } from "../types";

export interface RespaldosPort {
  listar(page?: number, pageSize?: number): Promise<RespaldosPaginados>;
  descargar(id: number): Promise<Blob>;
}
