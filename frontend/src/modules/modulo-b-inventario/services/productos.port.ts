// Puerto: interfaz de gestión de productos (listar, crear, actualizar).
import type { NuevoProducto, Producto } from "../types";

export interface ProductosPort {
  listar(busqueda?: string): Promise<Producto[]>;
  crear(datos: NuevoProducto): Promise<Producto>;
  actualizar(id: number, datos: Partial<NuevoProducto> & { activo?: boolean }): Promise<Producto>;
}
