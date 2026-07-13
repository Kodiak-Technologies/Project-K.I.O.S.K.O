// Puerto: interfaz de gestión de categorías.
import type { Categoria } from "../types";

export interface CategoriasPort {
  listar(): Promise<Categoria[]>;
  crear(nombre: string): Promise<Categoria>;
}
