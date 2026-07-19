# Entidades de dominio del Módulo B (Catálogo, Inventario y Aprobación de Ingresos).
#
# Python puro: sin imports de FastAPI ni SQLAlchemy. Las entidades representan
# reglas de negocio invariantes del dominio (RF-03/04/05/06/08/09/18/23/24/27).
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.value_objects import (
    EstadoMerma,
    EstadoSolicitud,
    MotivoMerma,
    TipoMovimiento,
    TipoPago,
    TipoPrecio,
)
from app.shared.kernel.base_entity import EntidadConBorradoLogico


# =============================================================================
# Catálogo: Producto y Categoria (EXTENDIDAS)
# =============================================================================


@dataclass(kw_only=True)
class Categoria(EntidadConBorradoLogico):
    """Categoría de productos (RF-04). Soft delete."""

    id: int | None
    nombre: str
    descripcion: str | None = None
    creado_por: int | None = None
    creado_por_nombre: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(kw_only=True)
class Producto:
    """Producto del catálogo (RF-03, RF-04, RF-08, RF-09, RF-18, RF-24).

    `precio` es el precio de venta actual (consumido por el Módulo C por SQL
    directo, RNF-03). `precio_compra_actual` es para márgenes. Soft delete.

    Nota: `kw_only=True` para que el orden de campos no rompa al agregar nuevos
    con default. Toda instanciación debe usar keyword args (consistente con
    el resto del módulo).
    """

    id: int | None
    codigo: str
    nombre: str
    categoria_id: int | None
    precio: Decimal
    stock: int = 0
    stock_minimo: int = 0
    activo: bool = True
    categoria: str | None = None  # nombre de la categoría (compat con skeleton)
    categoria_nombre: str | None = None  # nombre canónico según design
    precio_compra_actual: Decimal = Decimal("0")
    es_codigo_interno: bool = False
    foto_url: str | None = None
    creado_por: int | None = None
    creado_por_nombre: str | None = None
    actualizado_por: int | None = None
    actualizado_por_nombre: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by: int | None = None

    def disponible_para_venta(self) -> bool:
        return self.activo and self.stock > 0 and not self.eliminado

    def requiere_reposicion(self) -> bool:
        return self.activo and not self.eliminado and self.stock <= self.stock_minimo

    @property
    def eliminado(self) -> bool:
        return self.deleted_at is not None


# =============================================================================
# Solicitudes de ingreso (RF-05, RF-06, HU-B05/06/07/08)
# =============================================================================


@dataclass(kw_only=True)
class SolicitudIngreso(EntidadConBorradoLogico):
    """Cabecera de la solicitud de mercadería (flujo 2 pasos, D-09)."""

    id: int | None
    estado: EstadoSolicitud
    foto_boleta_url: str
    solicitado_por: int
    solicitado_por_nombre: str
    proveedor_id: int | None = None
    motivo_rechazo: str | None = None
    revisado_por: int | None = None
    revisado_por_nombre: str | None = None
    revisado_en: datetime | None = None
    lineas: list["DetalleSolicitud"] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def puede_ser_aprobada(self) -> bool:
        return self.estado == EstadoSolicitud("Pendiente") and not self.eliminado

    def puede_ser_rechazada(self) -> bool:
        return self.estado == EstadoSolicitud("Pendiente") and not self.eliminado

    def aprobar(self, usuario_id: int, nombre: str) -> None:
        """Transición de estado (regla D-09)."""
        from app.shared.kernel.exceptions import ConflictoError

        if not self.puede_ser_aprobada():
            raise ConflictoError("La solicitud ya fue revisada.")
        self.estado = EstadoSolicitud("Aprobada")
        self.revisado_por = usuario_id
        self.revisado_por_nombre = nombre
        # D-09 + chk_solicitudes_revisado_consistente: a reviewed request
        # MUST have a review timestamp. Set it in the same operation that
        # transitions the state, so the DB CHECK constraint is satisfied.
        self.revisado_en = datetime.now(timezone.utc)

    def rechazar(self, usuario_id: int, nombre: str, motivo: str) -> None:
        """Transición de estado con motivo obligatorio (D-09)."""
        from app.shared.kernel.exceptions import ConflictoError, ValidacionError

        if not self.puede_ser_rechazada():
            raise ConflictoError("La solicitud ya fue revisada.")
        motivo_limpio = (motivo or "").strip()
        if len(motivo_limpio) < 5:
            raise ValidacionError("El motivo de rechazo debe tener al menos 5 caracteres.")
        self.estado = EstadoSolicitud("Rechazada")
        self.motivo_rechazo = motivo_limpio
        self.revisado_por = usuario_id
        self.revisado_por_nombre = nombre
        # D-09 + chk_solicitudes_revisado_consistente: same as aprobar() —
        # the reject path was a latent twin of the bug, fixed preemptively.
        self.revisado_en = datetime.now(timezone.utc)


@dataclass(kw_only=True)
class DetalleSolicitud:
    """Línea de una solicitud de ingreso (HU-B05). Sin soft delete."""

    id: int | None
    solicitud_id: int
    producto_id: int
    cantidad: int
    precio_compra_unitario: Decimal
    created_at: datetime | None = None

    @classmethod
    def desde_dto(
        cls, producto_id: int, cantidad: int, precio: Decimal
    ) -> "DetalleSolicitud":
        return cls(
            id=None,
            solicitud_id=0,  # se asigna al persistir
            producto_id=producto_id,
            cantidad=cantidad,
            precio_compra_unitario=precio,
        )


# =============================================================================
# Mermas y pérdidas (RF-23, HU-B12, CU-B09b/c, D-14)
# =============================================================================


@dataclass(kw_only=True)
class Merma(EntidadConBorradoLogico):
    """Pérdida de inventario. Flujo de 2 pasos (D-14): cajero registra, ADMIN valida."""

    id: int | None
    producto_id: int
    cantidad: int
    motivo: MotivoMerma
    registrado_por: int
    registrado_por_nombre: str
    estado: EstadoMerma = field(default_factory=lambda: EstadoMerma("Registrada"))
    observacion: str | None = None
    proveedor_id: int | None = None
    motivo_rechazo: str | None = None
    confirmado_por: int | None = None
    confirmado_por_nombre: str | None = None
    confirmado_en: datetime | None = None
    rechazado_por: int | None = None
    rechazado_por_nombre: str | None = None
    rechazado_en: datetime | None = None
    created_at: datetime | None = None

    def puede_ser_confirmada(self) -> bool:
        return self.estado == EstadoMerma("Registrada") and not self.eliminado

    def puede_ser_rechazada(self) -> bool:
        return self.estado == EstadoMerma("Registrada") and not self.eliminado

    def confirmar(self, usuario_id: int, nombre: str) -> None:
        from app.shared.kernel.exceptions import ConflictoError

        if not self.puede_ser_confirmada():
            raise ConflictoError("La merma ya fue revisada.")
        self.estado = EstadoMerma("Confirmada")
        self.confirmado_por = usuario_id
        self.confirmado_por_nombre = nombre

    def rechazar(self, usuario_id: int, nombre: str, motivo: str) -> None:
        from app.shared.kernel.exceptions import ConflictoError, ValidacionError

        if not self.puede_ser_rechazada():
            raise ConflictoError("La merma ya fue revisada.")
        motivo_limpio = (motivo or "").strip()
        if len(motivo_limpio) < 5:
            raise ValidacionError("El motivo de rechazo debe tener al menos 5 caracteres.")
        self.estado = EstadoMerma("Rechazada")
        self.motivo_rechazo = motivo_limpio
        self.rechazado_por = usuario_id
        self.rechazado_por_nombre = nombre


# =============================================================================
# Proveedores y deuda (RF-27, HU-B14, D-12, D-15)
# =============================================================================


@dataclass(kw_only=True)
class Proveedor(EntidadConBorradoLogico):
    """Maestro de proveedores con control de deuda (denormalizado controlado, D-12)."""

    id: int | None
    razon_social: str
    creado_por: int
    creado_por_nombre: str
    ruc: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    activo: bool = True
    deuda_actual: Decimal = Decimal("0")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def tiene_deuda(self) -> bool:
        return self.deuda_actual > Decimal("0")

    def aplicar_delta_deuda(self, delta: Decimal) -> None:
        """Aplica un delta a la deuda (uso interno desde use cases transaccionales).

        Valida que el resultado no quede negativo.
        """
        from app.shared.kernel.exceptions import ValidacionError

        nuevo = self.deuda_actual + delta
        if nuevo < Decimal("0"):
            raise ValidacionError("La deuda no puede quedar negativa.")
        self.deuda_actual = nuevo


@dataclass(kw_only=True)
class PagoProveedor(EntidadConBorradoLogico):
    """Historial de movimientos de deuda con un proveedor (D-12, D-15)."""

    id: int | None
    proveedor_id: int
    tipo: TipoPago
    monto: Decimal
    fecha: datetime
    registrado_por: int
    registrado_por_nombre: str
    concepto: str | None = None
    solicitud_ingreso_id: int | None = None
    created_at: datetime | None = None

    @classmethod
    def crear_compra_credito(
        cls,
        proveedor_id: int,
        monto: Decimal,
        fecha: datetime,
        concepto: str | None,
        usuario_id: int,
        usuario_nombre: str,
        solicitud_ingreso_id: int | None = None,
    ) -> "PagoProveedor":
        return cls(
            id=None,
            proveedor_id=proveedor_id,
            tipo=TipoPago("compra_credito"),
            monto=monto,
            fecha=fecha,
            concepto=concepto,
            solicitud_ingreso_id=solicitud_ingreso_id,
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )

    @classmethod
    def crear_pago(
        cls,
        proveedor_id: int,
        monto: Decimal,
        fecha: datetime,
        concepto: str | None,
        usuario_id: int,
        usuario_nombre: str,
    ) -> "PagoProveedor":
        return cls(
            id=None,
            proveedor_id=proveedor_id,
            tipo=TipoPago("pago"),
            monto=monto,
            fecha=fecha,
            concepto=concepto,
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )


# =============================================================================
# Bitácoras append-only (sin soft delete; trigger BD refuerza inmutabilidad)
# =============================================================================


@dataclass(kw_only=True)
class MovimientoInventario:
    """Bitácora append-only de toda variación de stock (RF-08, D-07).

    El trigger `trg_historial_precios_no_update` se inspira en el patrón, pero
    para `movimientos_inventario` se aplica por convención (no hay trigger en BD
    en este PR). En PR2 se documenta explícitamente.
    """

    id: int | None
    producto_id: int
    cantidad: int
    tipo: TipoMovimiento
    registrado_por: int
    registrado_por_nombre: str
    motivo: str | None = None
    solicitud_ingreso_id: int | None = None
    merma_id: int | None = None
    created_at: datetime | None = None

    @classmethod
    def ingreso(
        cls,
        producto_id: int,
        cantidad: int,
        solicitud_ingreso_id: int,
        usuario_id: int,
        usuario_nombre: str,
    ) -> "MovimientoInventario":
        return cls(
            id=None,
            producto_id=producto_id,
            cantidad=cantidad,
            tipo=TipoMovimiento("ingreso"),
            solicitud_ingreso_id=solicitud_ingreso_id,
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )

    @classmethod
    def merma(
        cls,
        producto_id: int,
        cantidad: int,
        merma_id: int,
        motivo: str,
        usuario_id: int,
        usuario_nombre: str,
    ) -> "MovimientoInventario":
        return cls(
            id=None,
            producto_id=producto_id,
            cantidad=-cantidad,  # signo negativo porque es salida
            tipo=TipoMovimiento("merma"),
            motivo=motivo,
            merma_id=merma_id,
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )

    @classmethod
    def ajuste(
        cls,
        producto_id: int,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        usuario_nombre: str,
    ) -> "MovimientoInventario":
        return cls(
            id=None,
            producto_id=producto_id,
            cantidad=cantidad,
            tipo=TipoMovimiento("ajuste"),
            motivo=motivo,
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )

    @classmethod
    def venta(
        cls,
        producto_id: int,
        cantidad: int,
        usuario_id: int,
        usuario_nombre: str,
    ) -> "MovimientoInventario":
        """Factory opcional: el Módulo C coordina si inserta `tipo='venta'` (P-08)."""
        return cls(
            id=None,
            producto_id=producto_id,
            cantidad=-cantidad,
            tipo=TipoMovimiento("venta"),
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )

    @classmethod
    def devolucion(
        cls,
        producto_id: int,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        usuario_nombre: str,
    ) -> "MovimientoInventario":
        return cls(
            id=None,
            producto_id=producto_id,
            cantidad=cantidad,
            tipo=TipoMovimiento("devolucion"),
            motivo=motivo,
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )


@dataclass(kw_only=True)
class HistorialPrecio:
    """Bitácora inmutable de cambios de precio (HU-B11, D-06).

    El trigger `trg_historial_precios_no_update` en BD rechaza UPDATE/DELETE.
    `precio_anterior` es `None` en el alta inicial del producto.
    `id` es asignado por la BD en el INSERT; el adapter lo refresca con RETURNING.
    """

    id: int
    producto_id: int
    precio_nuevo: Decimal
    tipo_precio: TipoPrecio
    modificado_por: int
    modificado_por_nombre: str
    precio_anterior: Decimal | None = None
    created_at: datetime | None = None
