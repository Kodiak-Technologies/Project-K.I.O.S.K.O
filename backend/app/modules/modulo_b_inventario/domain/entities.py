# Entidades de dominio: Producto, Categoria, Almacen, MovimientoInventario, IngresoMercaderia, DetalleIngreso.
#
# NOTA (Clever): versión MÍNIMA (Producto/Categoria) para habilitar el POS del Módulo C.
# Brayan completa el resto de entidades de su módulo.
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Categoria:
    id: int | None
    nombre: str


@dataclass
class Producto:
    id: int | None
    codigo: str
    nombre: str
    categoria_id: int | None
    precio: Decimal
    stock: int = 0
    stock_minimo: int = 0
    activo: bool = True
    categoria: str | None = None  # nombre de la categoría, solo para mostrar
    created_at: datetime | None = None

    def disponible_para_venta(self) -> bool:
        return self.activo and self.stock > 0
