// Puerto: interfaz de gestión de categorías.
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/categorias_router.py
// NOTA: el backend devuelve `T[]` directo (sin paginación) en `GET /categorias`.
import type { Categoria, EdicionCategoria, NuevaCategoria } from "../types";

export interface CategoriasPort {
  /** `GET /categorias` — retorna `T[]` directo (sin paginar). */
  listar(): Promise<Categoria[]>;
  /** `POST /categorias`. */
  crear(datos: NuevaCategoria): Promise<Categoria>;
  /** `PATCH /categorias/{id}`. */
  editar(id: number, datos: EdicionCategoria): Promise<Categoria>;
}
