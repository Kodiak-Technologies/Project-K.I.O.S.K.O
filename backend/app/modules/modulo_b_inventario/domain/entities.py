# Entidades de dominio del Módulo B (Catálogo, Inventario y Aprobación de Ingresos).
#
# Python puro: sin imports de FastAPI ni SQLAlchemy. Las entidades representan
# reglas de negocio invariantes del dominio (RF-03/04/05/06/08/09/18/23/24/27).
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.value_objects import (
    EstadoSolicitud,
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
    # HU-B13: la alerta de stock mínimo se emite UNA sola vez por producto y se
    # rearma sola cuando el stock vuelve a superar el mínimo (ver
    # `incrementar_stock_atomic`).
    alerta_stock_notificada: bool = False
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
        # HU-B13: `stock_minimo = 0` significa "sin umbral definido"; esos
        # productos NO deben aparecer en la lista de reposición (si no, todo
        # producto agotado sin umbral genera ruido permanente).
        return (
            self.activo
            and not self.eliminado
            and self.stock_minimo > 0
            and self.stock <= self.stock_minimo
        )

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
    # sdd/modulo-b-aprobaciones-detalle-editar: free-text edit justification + audit triple.
    motivo: str | None = None
    editado_por: int | None = None
    editado_por_nombre: str | None = None
    editado_en: datetime | None = None

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

    # ====================================================================
    # sdd/modulo-b-aprobaciones-detalle-editar: editable cabecera + lineas
    # ====================================================================

    def puede_ser_editada_por(self, usuario_id: int, es_admin: bool) -> bool:
        """FR-3.1 + FR-3.2: editable only in Pendiente + (ADMIN or creator)."""
        return (
            self.estado == EstadoSolicitud("Pendiente")
            and not self.eliminado
            and (es_admin or self.solicitado_por == usuario_id)
        )

    def editar(
        self,
        *,
        editor_id: int,
        editor_nombre: str,
        es_admin: bool,
        proveedor_id: int | None = ...,
        motivo: str | None = ...,
        foto_boleta_url: str | None = ...,
        lineas_payload: list[tuple[int, int, "Decimal"]] | None = ...,
    ) -> tuple[dict, list["DetalleSolicitud"] | None]:
        """In-place mutation (FR-3.6). Returns (cabecera_changes, new_lineas_or_None).

        `cabecera_changes` is the dict of fields that actually changed (for
        the audit diff and the port's `actualizar_cabecera`). `lineas_or_None`
        is the full replacement list — None means "don't touch lineas" (per
        FR-3.4: only the array in the body, even `[]`, means "replace all").
        Use `...` (Ellipsis) as the sentinel for "not in body" (skipped).
        """
        from app.shared.kernel.exceptions import (
            ConflictoError,
            ProhibidoError,
            ValidacionError,
        )

        if not self.puede_ser_editada_por(editor_id, es_admin):
            if self.estado != EstadoSolicitud("Pendiente") or self.eliminado:
                raise ConflictoError(
                    "Esta solicitud ya no se puede editar.",
                    code="NOT_EDITABLE_STATE",
                )
            raise ProhibidoError(
                "No tenés permiso para editar esta solicitud.",
                code="FORBIDDEN",
            )

        cambios: dict = {}
        if proveedor_id is not ... and proveedor_id != self.proveedor_id:
            cambios["proveedor_id"] = proveedor_id
            self.proveedor_id = proveedor_id
        if motivo is not ... and motivo != self.motivo:
            cambios["motivo"] = motivo
            self.motivo = motivo
        if foto_boleta_url is not ... and foto_boleta_url != self.foto_boleta_url:
            cambios["foto_boleta_url"] = foto_boleta_url
            self.foto_boleta_url = foto_boleta_url

        # Replace-all semantics for lineas (FR-3.4). None = "no tocar".
        nuevas_lineas: list[DetalleSolicitud] | None = None
        if lineas_payload is not ... and lineas_payload is not None:
            for (pid, cant, precio) in lineas_payload:
                if cant <= 0:
                    raise ValidacionError(
                        "La cantidad debe ser mayor a 0.",
                        code="INVALID_LINE_VALUES",
                    )
                if precio < 0:
                    raise ValidacionError(
                        "El precio unitario debe ser mayor o igual a 0.",
                        code="INVALID_LINE_VALUES",
                    )
            nuevas_lineas = [
                DetalleSolicitud(
                    id=None,
                    solicitud_id=self.id or 0,  # filled in by repo
                    producto_id=pid,
                    cantidad=cant,
                    precio_compra_unitario=precio,
                )
                for (pid, cant, precio) in lineas_payload
            ]

        # Always set audit fields (FR-3.6.3: even no-op PATCH sets the editor).
        cambios["editado_por"] = editor_id
        cambios["editado_por_nombre"] = editor_nombre
        cambios["editado_en"] = datetime.now(timezone.utc)
        self.editado_por = editor_id
        self.editado_por_nombre = editor_nombre
        self.editado_en = cambios["editado_en"]

        return cambios, nuevas_lineas


@dataclass(kw_only=True)
class DetalleSolicitud:
    """Línea de una solicitud de ingreso (HU-B05). Sin soft delete."""

    id: int | None
    solicitud_id: int
    producto_id: int
    cantidad: int
    precio_compra_unitario: Decimal
    created_at: datetime | None = None
    # Datos del producto resueltos por JOIN al leer: evitan que el cliente
    # tenga que cargar el catálogo entero para traducir `producto_id`.
    producto_nombre: str | None = None
    producto_codigo: str | None = None

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
    created_at: datetime | None = None
    # Resueltos por JOIN al leer (ver DetalleSolicitud).
    producto_nombre: str | None = None
    producto_codigo: str | None = None

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
