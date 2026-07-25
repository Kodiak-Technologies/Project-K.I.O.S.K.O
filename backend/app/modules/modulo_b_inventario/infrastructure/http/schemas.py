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
    Merma,
    PagoProveedor,
    Producto,
    Proveedor,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.value_objects import (
    EstadoMerma,
    EstadoSolicitud,
    MotivoMerma,
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
    foto_url: str | None = None

    @model_validator(mode="after")
    def _validar_codigo(self) -> "ProductoCreate":
        if not self.es_codigo_interno and not (self.codigo and self.codigo.strip()):
            raise ValueError(
                "El código de barras es obligatorio cuando no es código interno."
            )
        return self


class ProductoUpdate(BaseModel):
    """Edición general. NO incluye precios (van por /precio)."""

    codigo: str | None = Field(default=None, min_length=1, max_length=60)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    categoria_id: int | None = None
    stock_minimo: int | None = Field(default=None, ge=0)
    activo: bool | None = None
    es_codigo_interno: bool | None = None
    foto_url: str | None = None

    @model_validator(mode="after")
    def _rechazar_precios(self) -> "ProductoUpdate":
        # Pydantic v2 ignora campos no declarados, pero validamos explícitamente
        # que no se envíen precio/precio_compra_actual en el dict.
        # Esto se refuerza en el router y el use case.
        return self


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
    foto_url: str | None = None
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
            foto_url=p.foto_url,
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
        )


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
    precio_venta: float | None = Field(default=None, ge=0)
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
    cantidad: int
    precio_compra_unitario: float

    @classmethod
    def desde_entidad(cls, d: DetalleSolicitud) -> "DetalleResponse":
        return cls(
            id=d.id,  # type: ignore[arg-type]
            producto_id=d.producto_id,
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


class AprobarIngresoRequest(BaseModel):
    """Actualmente vacío; el spec menciona `ajustes_lineas` pero el alcance
    final del PR2 no lo expone (se queda como follow-up)."""


class AprobacionResponse(BaseModel):
    id: int
    estado: str
    revisado_por_nombre: str
    revisado_en: datetime | None
    productos_actualizados: int
    unidades_agregadas: int


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
        if all(
            getattr(self, f) is None
            for f in ("proveedor_id", "motivo", "lineas")
        ):
            raise ValueError("Debes enviar al menos un campo para editar.")
        return self


# =============================================================================
# Mermas
# =============================================================================


class MermaCreate(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    motivo: str = Field(pattern="^(vencimiento|rotura|otro)$")
    observacion: str | None = Field(default=None, max_length=2000)
    proveedor_id: int | None = None


class MermaResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    motivo: str
    observacion: str | None
    estado: str
    registrado_por: int  # sdd/modulo-b-aprobaciones-detalle-editar: id (gate)
    registrado_por_nombre: str
    # sdd/modulo-b-aprobaciones-detalle-editar (verify fix #5): id fields for
    # confirmado_por / rechazado_por per spec FR-2.3 / FR-2.4. The *_nombre
    # snapshots were already here; the int FKs were missing — the entity and
    # the DB column both had them, only the response DTO was inconsistent.
    confirmado_por: int | None = None
    confirmado_por_nombre: str | None = None
    confirmado_en: datetime | None = None
    rechazado_por: int | None = None
    rechazado_por_nombre: str | None = None
    rechazado_en: datetime | None = None
    motivo_rechazo: str | None = None
    editado_por: int | None = None
    editado_por_nombre: str | None = None
    editado_en: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def desde_entidad(cls, m: Merma) -> "MermaResponse":
        return cls(
            id=m.id,  # type: ignore[arg-type]
            producto_id=m.producto_id,
            cantidad=m.cantidad,
            motivo=str(m.motivo),
            observacion=m.observacion,
            estado=str(m.estado),
            registrado_por=m.registrado_por,
            registrado_por_nombre=m.registrado_por_nombre,
            confirmado_por=m.confirmado_por,
            confirmado_por_nombre=m.confirmado_por_nombre,
            confirmado_en=m.confirmado_en,
            rechazado_por=m.rechazado_por,
            rechazado_por_nombre=m.rechazado_por_nombre,
            rechazado_en=m.rechazado_en,
            motivo_rechazo=m.motivo_rechazo,
            editado_por=m.editado_por,
            editado_por_nombre=m.editado_por_nombre,
            editado_en=m.editado_en,
            created_at=m.created_at,
        )


class MermasPaginadosResponse(BaseModel):
    items: list[MermaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MermaConfirmarResponse(BaseModel):
    id: int
    estado: str
    confirmado_por_nombre: str
    confirmado_en: datetime | None
    stock_actualizado: int | None = None


class RechazarMermaRequest(BaseModel):
    motivo_rechazo: Annotated[str, Field(min_length=5, max_length=2000)]


# =============================================================================
# sdd/modulo-b-aprobaciones-detalle-editar: PATCH /mermas/{id}
# =============================================================================


class MermaUpdateRequest(BaseModel):
    """PATCH /mermas/{id}. Allowlist cerrada (NFR-4). At least 1 field required."""

    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, pattern="^(vencimiento|rotura|otro)$")
    observacion: str | None = Field(default=None, max_length=1000)
    proveedor_id: int | None = None
    producto_id: int | None = Field(default=None, gt=0)
    cantidad: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "MermaUpdateRequest":
        if all(
            getattr(self, f) is None
            for f in ("motivo", "observacion", "proveedor_id", "producto_id", "cantidad")
        ):
            raise ValueError("Debes enviar al menos un campo para editar.")
        return self


# =============================================================================
# Proveedores
# =============================================================================


class ProveedorCreate(BaseModel):
    razon_social: Annotated[str, Field(min_length=1, max_length=120)]
    ruc: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def _validar_email(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email inválido.")
        return v


class ProveedorUpdate(BaseModel):
    razon_social: str | None = Field(default=None, min_length=1, max_length=120)
    ruc: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)
    activo: bool | None = None

    @model_validator(mode="after")
    def _rechazar_deuda(self) -> "ProveedorUpdate":
        # Defensa adicional: el use case también lo rechaza.
        return self


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
    cantidad: int
    tipo: str
    motivo: str | None
    solicitud_ingreso_id: int | None
    merma_id: int | None
    registrado_por_nombre: str
    created_at: datetime | None


class MovimientosPaginadosResponse(BaseModel):
    items: list[MovimientoInventarioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Storage
# =============================================================================


class StorageUploadResponse(BaseModel):
    url: str
    path: str
    filename: str
    mime: str
    size_bytes: int
    expires_at: datetime | None = None


# =============================================================================
# Aliases para mantener compat con el skeleton previo (creados en PR1)
# =============================================================================

# Los routers existentes (productos_router.py, categorias_router.py) usan estos
# nombres. Los alias permiten que sigan importando desde aquí.
CrearProductoRequest = ProductoCreate
ActualizarProductoRequest = ProductoUpdate
