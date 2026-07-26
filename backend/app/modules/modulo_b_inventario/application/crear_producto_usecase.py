# Caso de uso: crear un producto nuevo (HU-B01, HU-B03, REQ-04, REQ-08).
# Si `es_codigo_interno=true`, genera código con formato `PREFIJO-CORRELATIVO` (D-T02).
# Persiste fila inicial de `historial_precios` con `precio_anterior=None` (REQ-04).
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import HistorialPrecio, Producto
from app.modules.modulo_b_inventario.domain.ports.categoria_repository_port import (
    CategoriaRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.historial_precio_repository_port import (
    HistorialPrecioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import CodigoInterno, TipoPrecio
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)


def _tiene_formato_de_codigo_interno(codigo: str, prefijo: str) -> bool:
    """True si `codigo` puede confundirse con un código interno del sistema.

    Solo colisionan los que usan EL MISMO prefijo que genera el backend
    (`PAP-001`): un código manual tipo `BC-12345` es válido como código de
    barras y no se bloquea.
    """
    if not codigo.upper().startswith(f"{prefijo}-"):
        return False
    try:
        CodigoInterno(codigo.upper())
    except ValidacionError:
        return False
    return True


class CrearProductoUseCase:
    # D-T02: prefijo de los códigos internos (PAP-001, PAP-002, ...).
    PREFIJO = "PAP"

    def __init__(
        self,
        producto_repo: ProductoRepositoryPort,
        categoria_repo: CategoriaRepositoryPort,
        historial_repo: HistorialPrecioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._productos = producto_repo
        self._categorias = categoria_repo
        self._historial = historial_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        *,
        codigo: str | None,
        nombre: str,
        categoria_id: int | None,
        precio_venta: Decimal,
        precio_compra_actual: Decimal,
        stock_minimo: int = 0,
        stock_inicial: int = 0,
        es_codigo_interno: bool = False,
        foto_url: str | None = None,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Producto:
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValidacionError("El nombre del producto es obligatorio.")
        if precio_venta <= 0:
            raise ValidacionError("El precio de venta debe ser mayor a 0.")
        if precio_compra_actual < 0:
            raise ValidacionError("El precio de compra no puede ser negativo.")
        if stock_inicial < 0 or stock_minimo < 0:
            raise ValidacionError("El stock no puede ser negativo.")

        # Resolver código (interno autogenerado o barcode manual)
        if es_codigo_interno:
            codigo = await self._generar_codigo_interno()
        else:
            if not codigo or not codigo.strip():
                raise ValidacionError(
                    "El código de barras es obligatorio cuando no es código interno."
                )
            codigo = codigo.strip()
            # HU-B03: el código de barras NO puede colisionar con el formato de
            # los códigos internos (PAP-001). Antes el `raise` estaba dentro del
            # `try` y lo capturaba su propio `except ValidacionError`, así que la
            # validación nunca se aplicaba.
            if _tiene_formato_de_codigo_interno(codigo, self.PREFIJO):
                raise ValidacionError(
                    "El código enviado tiene formato de código interno "
                    f"({self.PREFIJO}-NNN); marca es_codigo_interno=true."
                )

        # Unicidad (incluye borrados lógicos: el UNIQUE de la tabla es global)
        if await self._productos.existe_codigo(codigo):
            raise ConflictoError(f"Ya existe un producto con el código '{codigo}'.")

        # Validar categoría si se da
        if categoria_id is not None:
            cat = await self._categorias.find_by_id(categoria_id)
            if cat is None:
                raise NoEncontradoError("Categoría no encontrada.")

        creado = await self._productos.crear(
            Producto(
                id=None,
                codigo=codigo,
                nombre=nombre,
                categoria_id=categoria_id,
                precio=Decimal(str(precio_venta)),
                precio_compra_actual=Decimal(str(precio_compra_actual)),
                stock=stock_inicial,
                stock_minimo=stock_minimo,
                activo=True,
                es_codigo_interno=es_codigo_interno,
                foto_url=foto_url,
                creado_por=usuario_id,
                creado_por_nombre=usuario_nombre,
            )
        )

        # Fila inicial de historial_precios (precio_anterior=None)
        await self._historial.append(
            HistorialPrecio(
                id=0,  # placeholder; el adapter lo asigna con RETURNING id
                producto_id=creado.id,
                precio_nuevo=creado.precio,
                tipo_precio=TipoPrecio("venta"),
                modificado_por=usuario_id,
                modificado_por_nombre=usuario_nombre,
                precio_anterior=None,
            )
        )
        if creado.precio_compra_actual and creado.precio_compra_actual > 0:
            await self._historial.append(
                HistorialPrecio(
                    id=0,  # placeholder; el adapter lo asigna con RETURNING id
                    producto_id=creado.id,
                    precio_nuevo=creado.precio_compra_actual,
                    tipo_precio=TipoPrecio("compra"),
                    modificado_por=usuario_id,
                    modificado_por_nombre=usuario_nombre,
                    precio_anterior=None,
                )
            )

        await self._auditoria.ejecutar(
            accion="producto_creado",
            entidad="productos",
            usuario_id=usuario_id,
            rol="",
            entidad_id=creado.id,
            valor_nuevo={
                "codigo": creado.codigo,
                "nombre": creado.nombre,
                "precio_venta": float(creado.precio),
                "precio_compra_actual": float(creado.precio_compra_actual),
                "stock": creado.stock,
                "stock_minimo": creado.stock_minimo,
                "categoria_id": creado.categoria_id,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return creado

    async def _generar_codigo_interno(self) -> str:
        """D-T02 / HU-B03: `PREFIJO-CORRELATIVO` real (PAP-001, PAP-002, ...).

        Antes se usaba `PAP-{HHMMSS}` y, ante colisión, se concatenaba una "X"
        (`PAP-223902X`), que ni es correlativo ni cumple el patrón del VO.
        """
        correlativo = await self._productos.siguiente_correlativo_interno(self.PREFIJO)
        # 3 dígitos mientras alcance; a partir de 1000 crece solo (el VO admite 3-6).
        candidato = f"{self.PREFIJO}-{correlativo:03d}"
        CodigoInterno(candidato)  # valida el formato antes de persistir
        return candidato
