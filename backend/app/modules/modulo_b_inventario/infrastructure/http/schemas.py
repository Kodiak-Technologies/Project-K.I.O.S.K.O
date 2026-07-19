# DTOs Pydantic (request/response) del módulo de inventario.
# Contrato con el frontend: docs/FRONTEND_CONTRATOS_API.md (Módulo B).
from pydantic import BaseModel, Field

from app.modules.modulo_b_inventario.domain.entities import Categoria, Producto


class ProductoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    categoria_id: int | None
    categoria: str | None
    precio: float
    stock: int
    stock_minimo: int
    activo: bool

    @classmethod
    def desde_entidad(cls, p: Producto) -> "ProductoResponse":
        return cls(
            id=p.id, codigo=p.codigo, nombre=p.nombre,
            categoria_id=p.categoria_id, categoria=p.categoria,
            precio=float(p.precio), stock=p.stock, stock_minimo=p.stock_minimo,
            activo=p.activo,
        )


class CrearProductoRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    nombre: str = Field(min_length=1, max_length=150)
    categoria_id: int | None = None
    precio: float = Field(gt=0)
    stock_minimo: int = Field(default=0, ge=0)
    # Extensión al contrato: permite dar de alta con existencias iniciales
    # (el flujo formal de reposición es el de ingresos aprobados de Brayan).
    stock_inicial: int = Field(default=0, ge=0)


class ActualizarProductoRequest(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=60)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    categoria_id: int | None = None
    precio: float | None = Field(default=None, gt=0)
    stock_minimo: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class CategoriaResponse(BaseModel):
    id: int
    nombre: str

    @classmethod
    def desde_entidad(cls, c: Categoria) -> "CategoriaResponse":
        return cls(id=c.id, nombre=c.nombre)


class CrearCategoriaRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
