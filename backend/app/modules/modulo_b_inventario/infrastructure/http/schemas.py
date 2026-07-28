# DTOs Pydantic (request/response) del módulo de inventario.
# Contrato con el frontend: docs/Cambios-Brayan/API_MODULO_B.md.
# Convenciones:
#   - Mensajes en español.
#   - `Field(...)` para rangos/longitudes; `model_validator(mode="after")` para
#     reglas cross-field (D-T05).
#   - `desde_entidad(entidad)` para los responses.
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.modulo_b_inventario.domain.entities import (
    Categoria,
    DetalleSolicitud,
    HistorialPrecio,
    PagoProveedor,
    Producto,
    Proveedor,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.value_objects import (
    EstadoSolicitud,
    TipoMovimiento,
    TipoPago,
    TipoPrecio,
)
from app.modules.modulo_b_inventario.application.listar_productos_por_reponer_usecase import (
    PorReponerItem,
)


# =============================================================================
# Paginación (helper)
# =============================================================================


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Número de página (>=1)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Tamaño de página (1-100)"
    )


# =============================================================================
# Productos y categorías
# =============================================================================


class CategoriaCreate(BaseModel):
    nombre: Annotated[str, Field(min_length=1, max_length=80)]
    descripcion: str | None = Field(default=None, max_length=500)


class CategoriaUpdate(BaseModel):
    nombre: Annotated[str | None, Field(default=None, min_length=1, max_length=80)]
    descripcion: str | None = Field(default=None, max_length=500)
    activo: bool | None = None


class CategoriaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    activo: bool = True
    creado_por_nombre: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def desde_entidad(cls, c: Categoria) -> "CategoriaResponse":
        return cls(
            id=c.id,  # type: ignore[arg-type]
            nombre=c.nombre,
            descripcion=c.descripcion,
            activo=c.deleted_at is None,
            creado_por_nombre=c.creado_por_nombre,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class ProductoCreate(BaseModel):
    """Alta de producto. `extra="forbid"`: campos que ya no existen (p. ej.
    `foto_url`) se rechazan con 422 en vez de descartarse en silencio."""

    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, max_length=60)
    nombre: Annotated[str, Field(min_length=1, max_length=150)]
    categoria_id: int | None = None
    precio_venta: float = Field(gt=0, description="Precio de venta (debe ser > 0)")
    precio_compra_actual: float = Field(
        default=0, ge=0, description="Precio de compra actual (>= 0)"
    )
    stock_minimo: int = Field(default=0, ge=0)
    stock_inicial: int = Field(default=0, ge=0)
    es_codigo_interno: bool = False

    @model_validator(mode="after")
    def _validar_codigo(self) -> "ProductoCreate":
        if not self.es_codigo_interno and not (self.codigo and self.codigo.strip()):
            raise ValueError(
                "El código de barras es obligatorio cuando no es código interno."
            )
        return self


class ProductoUpdate(BaseModel):
    """Edición general. NO incluye precios (van por /precio).

    `extra="forbid"`: mandar `precio` o `precio_compra_actual` acá devuelve 422.
    Antes Pydantic los descartaba en silencio y el PATCH respondía 200 sin haber
    cambiado el precio (el usuario creía que sí).
    """

    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, min_length=1, max_length=60)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    categoria_id: int | None = None
    stock_minimo: int | None = Field(default=None, ge=0)
    activo: bool | None = None
    es_codigo_interno: bool | None = None

    def cambios(self) -> dict:
        """Campos realmente enviados (los ausentes no se tocan)."""
        return self.model_dump(exclude_unset=True)


class ProductoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    categoria_id: int | None
    categoria_nombre: str | None
    precio: float
    precio_compra_actual: float
    stock: int
    stock_minimo: int
    activo: bool
    es_codigo_interno: bool
    creado_por_nombre: str | None = None
    actualizado_por_nombre: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def desde_entidad(cls, p: Producto) -> "ProductoResponse":
        return cls(
            id=p.id,  # type: ignore[arg-type]
            codigo=p.codigo,
            nombre=p.nombre,
            categoria_id=p.categoria_id,
            categoria_nombre=p.categoria_nombre or p.categoria,
            precio=float(p.precio),
            precio_compra_actual=float(p.precio_compra_actual),
            stock=p.stock,
            stock_minimo=p.stock_minimo,
            activo=p.activo,
            es_codigo_interno=p.es_codigo_interno,
            creado_por_nombre=p.creado_por_nombre,
            actualizado_por_nombre=p.actualizado_por_nombre,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )


class PorReponerItemResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    categoria_id: int | None
    categoria_nombre: str | None
    stock: int
    stock_minimo: int
    faltante: int
    # HU-B13: si ya se avisó, no hay que volver a alertar hasta la reposición.
    alerta_notificada: bool = False

    @classmethod
    def desde_item(cls, item: PorReponerItem) -> "PorReponerItemResponse":
        p = item.producto
        return cls(
            id=p.id,  # type: ignore[arg-type]
            codigo=p.codigo,
            nombre=p.nombre,
            categoria_id=p.categoria_id,
            categoria_nombre=p.categoria_nombre or p.categoria,
            stock=p.stock,
            stock_minimo=p.stock_minimo,
            faltante=item.faltante,
            alerta_notificada=p.alerta_stock_notificada,
        )


class MarcarAlertasRequest(BaseModel):
    """HU-B13: marca como avisadas las alertas de stock mínimo ya mostradas."""

    model_config = ConfigDict(extra="forbid")

    producto_ids: list[int] = Field(min_length=1)


class MarcarAlertasResponse(BaseModel):
    marcados: int


# =============================================================================
# Catálogo del ADMIN: ajuste manual de stock y baja de producto
# =============================================================================


class AjustarStockRequest(BaseModel):
    """`POST /productos/{id}/ajustar-stock` (solo ADMIN).

    `delta` positivo suma, negativo descuenta. El motivo queda en el asiento de
    `movimientos_inventario` y en la bitácora.
    """

    model_config = ConfigDict(extra="forbid")

    delta: int = Field(description="Unidades a sumar (+) o descontar (-). Distinto de 0.")
    motivo: Annotated[str, Field(min_length=3, max_length=200)]

    @model_validator(mode="after")
    def _delta_no_cero(self) -> "AjustarStockRequest":
        if self.delta == 0:
            raise ValueError("El ajuste debe ser distinto de 0.")
        return self


class AjusteStockResponse(BaseModel):
    producto: ProductoResponse
    stock_anterior: int
    stock_actual: int
    delta: int


class EliminarProductoRequest(BaseModel):
    """Body opcional de `DELETE /productos/{id}`."""

    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, max_length=200)


class ProductosPaginadosResponse(BaseModel):
    items: list[ProductoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PorReponerPaginadosResponse(BaseModel):
    items: list[PorReponerItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Cambio de precio (HU-B11)
# =============================================================================


class CambiarPrecioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # `gt=0`: el alta exige precio de venta > 0, el cambio de precio también
    # (antes se podía dejar un producto en 0.00 y seguía vendiéndose).
    precio_venta: float | None = Field(default=None, gt=0)
    precio_compra_actual: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _al_menos_uno(self) -> "CambiarPrecioRequest":
        if self.precio_venta is None and self.precio_compra_actual is None:
            raise ValueError(
                "Debes enviar al menos uno: precio_venta o precio_compra_actual."
            )
        return self


class CambiarPrecioResponse(BaseModel):
    producto: ProductoResponse
    historial_registrado: bool
    filas_historial: list["HistorialPrecioResponse"]

    @classmethod
    def desde(
        cls,
        producto,
        historial_registrado: bool,
        filas: list[HistorialPrecio],
    ) -> "CambiarPrecioResponse":
        return cls(
            producto=ProductoResponse.desde_entidad(producto),
            historial_registrado=historial_registrado,
            filas_historial=[HistorialPrecioResponse.desde_entidad(f) for f in filas],
        )


# =============================================================================
# Historial de precios
# =============================================================================


class HistorialPrecioResponse(BaseModel):
    id: int
    tipo_precio: str
    precio_anterior: float | None
    precio_nuevo: float
    modificado_por_nombre: str
    created_at: datetime | None = None

    @classmethod
    def desde_entidad(cls, h: HistorialPrecio) -> "HistorialPrecioResponse":
        return cls(
            id=h.id,  # type: ignore[arg-type]
            tipo_precio=str(h.tipo_precio),
            precio_anterior=float(h.precio_anterior) if h.precio_anterior is not None else None,
            precio_nuevo=float(h.precio_nuevo),
            modificado_por_nombre=h.modificado_por_nombre,
            created_at=h.created_at,
        )


class HistorialPaginadosResponse(BaseModel):
    items: list[HistorialPrecioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Solicitudes de ingreso
# =============================================================================


class DetalleCreate(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    precio_compra_unitario: float = Field(ge=0)


class SolicitudIngresoCreate(BaseModel):
    proveedor_id: int | None = None
    foto_boleta_url: Annotated[str, Field(min_length=1, max_length=2000)]
    lineas: list[DetalleCreate]

    @model_validator(mode="after")
    def _validar_lineas(self) -> "SolicitudIngresoCreate":
        if not self.lineas:
            raise ValueError("La solicitud debe tener al menos una línea.")
        return self


class DetalleResponse(BaseModel):
    id: int
    producto_id: int
    # Resueltos por JOIN: el cliente no necesita cargar el catálogo para
    # mostrar el nombre de la línea.
    producto_nombre: str | None = None
    producto_codigo: str | None = None
    cantidad: int
    precio_compra_unitario: float

    @classmethod
    def desde_entidad(cls, d: DetalleSolicitud) -> "DetalleResponse":
        return cls(
            id=d.id,  # type: ignore[arg-type]
            producto_id=d.producto_id,
            producto_nombre=d.producto_nombre,
            producto_codigo=d.producto_codigo,
            cantidad=d.cantidad,
            precio_compra_unitario=float(d.precio_compra_unitario),
        )


class SolicitudIngresoResponse(BaseModel):
    id: int
    proveedor_id: int | None
    estado: str
    foto_boleta_url: str
    motivo_rechazo: str | None
    motivo: str | None = None  # sdd/modulo-b-aprobaciones-detalle-editar
    lineas: list[DetalleResponse]
    solicitado_por: int  # sdd/modulo-b-aprobaciones-detalle-editar: id (gate)
    solicitado_por_nombre: str
    revisado_por_nombre: str | None
    revisado_en: datetime | None
    editado_por: int | None = None
    editado_por_nombre: str | None = None
    editado_en: datetime | None = None
    created_at: datetime | None
    updated_at: datetime | None = None
    cantidad_productos: int | None = None
    monto_total: float | None = None

    @classmethod
    def desde_entidad(
        cls,
        s: SolicitudIngreso,
        *,
        cantidad_productos: int | None = None,
        monto_total: float | None = None,
    ) -> "SolicitudIngresoResponse":
        return cls(
            id=s.id,  # type: ignore[arg-type]
            proveedor_id=s.proveedor_id,
            estado=str(s.estado),
            foto_boleta_url=s.foto_boleta_url,
            motivo_rechazo=s.motivo_rechazo,
            motivo=s.motivo,
            lineas=[DetalleResponse.desde_entidad(l) for l in s.lineas],
            solicitado_por=s.solicitado_por,
            solicitado_por_nombre=s.solicitado_por_nombre,
            revisado_por_nombre=s.revisado_por_nombre,
            revisado_en=s.revisado_en,
            editado_por=s.editado_por,
            editado_por_nombre=s.editado_por_nombre,
            editado_en=s.editado_en,
            created_at=s.created_at,
            updated_at=s.updated_at,
            cantidad_productos=cantidad_productos,
            monto_total=monto_total,
        )


class IngresosPaginadosResponse(BaseModel):
    items: list[SolicitudIngresoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    # Cursor de la última fila: mandalo como `cursor` para pedir el tramo
    # siguiente sin que las escrituras de arriba corran las páginas.
    siguiente_cursor: str | None = None


class AprobarIngresoRequest(BaseModel):
    """Body opcional de la aprobación (HU-B07 + HU-B14)."""

    model_config = ConfigDict(extra="forbid")

    registrar_credito: bool = Field(
        default=False,
        description=(
            "Si es true, carga el monto del ingreso a la deuda del proveedor "
            "como compra a crédito, vinculada a esta solicitud."
        ),
    )


class AprobacionResponse(BaseModel):
    id: int
    estado: str
    revisado_por_nombre: str
    revisado_en: datetime | None
    productos_actualizados: int
    unidades_agregadas: int
    monto_total: float = 0.0
    credito_registrado: bool = False


class RechazarIngresoRequest(BaseModel):
    motivo_rechazo: Annotated[str, Field(min_length=5, max_length=2000)]


# =============================================================================
# sdd/modulo-b-aprobaciones-detalle-editar: PATCH /ingresos/{id}
# =============================================================================


class LineaIngresoUpdateItem(BaseModel):
    """Línea dentro del PATCH /ingresos. producto_id OBLIGATORIO, cantidad>0, precio>=0."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)


class SolicitudIngresoUpdateRequest(BaseModel):
    """PATCH /ingresos/{id}. Allowlist cerrada (NFR-4). At least 1 field required (FR-3.3.2).

    Nota: `observaciones` y `foto_boleta_url` se aceptan pero NO se persisten
    en esta versión (la entidad no tiene esos campos persistibles; el spec lo
    documenta en el §10 de decisiones).
    """

    model_config = ConfigDict(extra="forbid")

    proveedor_id: int | None = None
    motivo: str | None = Field(default=None, max_length=500)
    lineas: list[LineaIngresoUpdateItem] | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "SolicitudIngresoUpdateRequest":
        # `model_fields_set` = campos realmente presentes en el body. Con la
        # comprobación anterior (todos None), mandar `{"motivo": null}` para
        # limpiar el campo se rechazaba, y peor: los campos ausentes viajaban
        # como None al use case y BORRABAN el valor guardado.
        if not self.model_fields_set:
            raise ValueError("Debes enviar al menos un campo para editar.")
        return self

    def valor(self, campo: str):
        """Valor del campo si vino en el body; `...` (sentinel) si no vino."""
        return getattr(self, campo) if campo in self.model_fields_set else ...


# =============================================================================
# Proveedores
# =============================================================================


def _normalizar_email(v: str | None) -> str | None:
    """Valida un email opcional. Compartido por el alta y la edición."""
    if v is None or v.strip() == "":
        return None
    if "@" not in v or "." not in v.split("@")[-1]:
        raise ValueError("Email inválido.")
    return v


class ProveedorCreate(BaseModel):
    razon_social: Annotated[str, Field(min_length=1, max_length=120)]
    ruc: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def _validar_email(cls, v: str | None) -> str | None:
        return _normalizar_email(v)


class ProveedorUpdate(BaseModel):
    """`extra="forbid"`: `deuda_actual` solo se mueve con compras/pagos."""

    model_config = ConfigDict(extra="forbid")

    razon_social: str | None = Field(default=None, min_length=1, max_length=120)
    ruc: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)
    activo: bool | None = None

    # Mismo criterio que el alta: antes el PATCH aceptaba cualquier cadena.
    @field_validator("email")
    @classmethod
    def _validar_email(cls, v: str | None) -> str | None:
        return _normalizar_email(v)


class ProveedorResponse(BaseModel):
    id: int
    razon_social: str
    ruc: str | None
    telefono: str | None
    email: str | None
    direccion: str | None
    activo: bool
    deuda_actual: float
    creado_por_nombre: str
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def desde_entidad(cls, p: Proveedor) -> "ProveedorResponse":
        return cls(
            id=p.id,  # type: ignore[arg-type]
            razon_social=p.razon_social,
            ruc=p.ruc,
            telefono=p.telefono,
            email=p.email,
            direccion=p.direccion,
            activo=p.activo,
            deuda_actual=float(p.deuda_actual),
            creado_por_nombre=p.creado_por_nombre,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )


class ProveedoresPaginadosResponse(BaseModel):
    items: list[ProveedorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Pagos a proveedor
# =============================================================================


class PagoProveedorCreate(BaseModel):
    """Body de `/compras-credito` y de `/pagos`.

    `solicitud_ingreso_id` solo tiene sentido en una compra a crédito (el CHECK
    `chk_pagos_solicitud_solo_en_compra` lo exige); el router de pagos lo
    rechaza con 422 en vez de descartarlo en silencio.
    """

    model_config = ConfigDict(extra="forbid")

    monto: float = Field(gt=0)
    fecha: date
    concepto: str | None = Field(default=None, max_length=500)
    solicitud_ingreso_id: int | None = None


class PagoProveedorResponse(BaseModel):
    id: int
    tipo: str
    monto: float
    concepto: str | None
    fecha: date
    solicitud_ingreso_id: int | None
    registrado_por_nombre: str
    created_at: datetime | None
    deuda_actual: float  # Estado actual de la deuda del proveedor tras la operación.

    @classmethod
    def desde_entidad(
        cls, p: PagoProveedor, deuda_actual: float
    ) -> "PagoProveedorResponse":
        return cls(
            id=p.id,  # type: ignore[arg-type]
            tipo=str(p.tipo),
            monto=float(p.monto),
            concepto=p.concepto,
            fecha=p.fecha.date() if isinstance(p.fecha, datetime) else p.fecha,
            solicitud_ingreso_id=p.solicitud_ingreso_id,
            registrado_por_nombre=p.registrado_por_nombre,
            created_at=p.created_at,
            deuda_actual=deuda_actual,
        )


class PagosPaginadosResponse(BaseModel):
    items: list[PagoProveedorResponse]
    deuda_actual: float
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Movimientos de inventario
# =============================================================================


class MovimientoInventarioResponse(BaseModel):
    id: int
    producto_id: int
    producto_nombre: str | None = None
    producto_codigo: str | None = None
    cantidad: int
    tipo: str
    motivo: str | None
    solicitud_ingreso_id: int | None
    registrado_por_nombre: str
    created_at: datetime | None


class MovimientosPaginadosResponse(BaseModel):
    items: list[MovimientoInventarioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    # Cursor de la última fila: mandalo como `cursor` para pedir el tramo
    # siguiente sin que las escrituras de arriba corran las páginas.
    siguiente_cursor: str | None = None


# =============================================================================
# Storage
# =============================================================================


class StorageUploadResponse(BaseModel):
    url: str
    #: `file_id` de Drive.
    path: str
    filename: str
    mime: str
    size_bytes: int


# =============================================================================
# Aliases para mantener compat con el skeleton previo (creados en PR1)
# =============================================================================

# Los routers existentes (productos_router.py, categorias_router.py) usan estos
# nombres. Los alias permiten que sigan importando desde aquí.
CrearProductoRequest = ProductoCreate
ActualizarProductoRequest = ProductoUpdate
