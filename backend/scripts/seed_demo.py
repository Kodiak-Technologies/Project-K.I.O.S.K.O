# Datos de demostración para desarrollo: categorías, proveedores y productos
# de un kiosco peruano, con precios y márgenes coherentes.
#
# NO es el seed mínimo del sistema (ese vive en `db/schema.sql` y en
# `scripts/seed.py`): esto es sólo para tener con qué probar la app.
#
# Idempotente: se puede correr varias veces. Las categorías se identifican por
# nombre, los proveedores por RUC y los productos por código de barras; si ya
# existen, se omiten.
#
# Uso:  python -m scripts.seed_demo
import asyncio
import sys
from decimal import Decimal

from sqlalchemy import select

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    UsuarioModel,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
    ProductoModel,
    ProveedorModel,
)
from app.shared.database.session import SessionLocal, engine

# -----------------------------------------------------------------------------
# Categorías
# -----------------------------------------------------------------------------
CATEGORIAS = [
    ("Galletas", "Galletas dulces, saladas y wafers"),
    ("Refrescos y gaseosas", "Bebidas sin alcohol, jugos y aguas"),
    ("Embutidos", "Jamonada, hot dog, chorizo y fiambres"),
    ("Lácteos", "Leche, yogurt, quesos y mantequilla"),
    ("Snacks", "Papas fritas, chizitos, maní y piqueos"),
    ("Golosinas", "Chocolates, caramelos y chupetines"),
    ("Abarrotes", "Arroz, azúcar, aceite y menestras"),
    ("Fideos y pastas", "Spaghetti, tallarín y sopas"),
    ("Conservas", "Atún, leche evaporada y enlatados"),
    ("Panadería", "Pan de molde, keke y tostadas"),
    ("Limpieza", "Detergente, lejía y lavavajilla"),
    ("Higiene personal", "Jabón, papel higiénico y shampoo"),
]

# -----------------------------------------------------------------------------
# Proveedores — nombres y RUC inventados (no corresponden a empresas reales),
# con formato válido: RUC de 11 dígitos que empieza en 20 (persona jurídica).
# -----------------------------------------------------------------------------
PROVEEDORES = [
    ("Distribuidora Andina del Norte S.A.C.", "20481234567", "986541230",
     "ventas@distandina.pe", "Av. Argentina 2145, Cercado de Lima"),
    ("Comercial Los Portales E.I.R.L.", "20512347896", "998745612",
     "pedidos@losportales.pe", "Jr. Cusco 480, La Victoria, Lima"),
    ("Alimentos del Sur S.A.C.", "20556789012", "945120368",
     "contacto@alimentosdelsur.pe", "Av. Nicolás Ayllón 3820, Ate"),
    ("Lácteos y Derivados Huaral S.R.L.", "20603456781", "912457893",
     "administracion@lacteoshuaral.pe", "Carretera Chancay-Huaral Km 4"),
    ("Embutidos San Isidro S.A.C.", "20478912345", "977321654",
     "ventas@embutidossanisidro.pe", "Av. Colonial 1580, Callao"),
    ("Golosinas y Snacks Perú S.A.C.", "20591234568", "965478213",
     "pedidos@golosinasperu.pe", "Jr. Paruro 1120, Cercado de Lima"),
    ("Droguería e Higiene Lima S.A.C.", "20624567893", "934871256",
     "compras@higienelima.pe", "Av. Venezuela 2450, Breña"),
    ("Panificadora El Trigal E.I.R.L.", "20537891234", "921654870",
     "elrigal@panificadora.pe", "Av. Universitaria 4210, Los Olivos"),
]

# -----------------------------------------------------------------------------
# Productos: (categoría, nombre, precio_venta, precio_compra, stock, stock_mínimo)
# Precios en soles, con margen realista de kiosco (~25-35%).
# -----------------------------------------------------------------------------
PRODUCTOS = [
    # Galletas
    ("Galletas", "Galleta Soda Field paquete 6 unid.", "3.50", "2.60", 48, 12),
    ("Galletas", "Galleta Casino chocolate 6 unid.", "3.80", "2.80", 36, 12),
    ("Galletas", "Galleta Margarita vainilla 6 unid.", "3.50", "2.60", 30, 12),
    ("Galletas", "Galleta Oreo original 6 unid.", "5.50", "4.20", 24, 8),
    ("Galletas", "Galleta Morochas chocolate 6 unid.", "3.80", "2.80", 40, 12),
    ("Galletas", "Wafer Chomp fresa 6 unid.", "3.20", "2.30", 18, 10),
    # Refrescos y gaseosas
    ("Refrescos y gaseosas", "Inca Kola 500 ml", "3.00", "2.20", 60, 24),
    ("Refrescos y gaseosas", "Coca Cola 500 ml", "3.00", "2.20", 55, 24),
    ("Refrescos y gaseosas", "Inca Kola 1.5 L", "7.50", "5.80", 24, 8),
    ("Refrescos y gaseosas", "Coca Cola 1.5 L", "7.50", "5.80", 20, 8),
    ("Refrescos y gaseosas", "Agua San Luis sin gas 625 ml", "1.80", "1.20", 72, 24),
    ("Refrescos y gaseosas", "Agua San Luis con gas 625 ml", "1.80", "1.20", 30, 12),
    ("Refrescos y gaseosas", "Frugos Del Valle durazno 300 ml", "2.50", "1.80", 36, 12),
    ("Refrescos y gaseosas", "Sporade tropical 500 ml", "3.20", "2.40", 28, 12),
    ("Refrescos y gaseosas", "Pepsi 500 ml", "2.80", "2.00", 32, 12),
    # Embutidos
    ("Embutidos", "Jamonada San Fernando 500 g", "12.90", "9.80", 12, 4),
    ("Embutidos", "Hot dog San Fernando 8 unid.", "9.50", "7.20", 15, 6),
    ("Embutidos", "Chorizo parrillero Otto Kunz 400 g", "16.90", "13.00", 8, 3),
    ("Embutidos", "Jamón inglés Braedt 200 g", "11.50", "8.60", 10, 4),
    ("Embutidos", "Salchicha huachana 500 g", "13.50", "10.20", 6, 3),
    # Lácteos
    ("Lácteos", "Leche Gloria evaporada 400 g", "4.50", "3.50", 60, 24),
    ("Lácteos", "Leche fresca Laive 1 L", "6.80", "5.30", 18, 6),
    ("Lácteos", "Yogurt Gloria fresa 1 L", "7.90", "6.10", 15, 6),
    ("Lácteos", "Yogurt Laive durazno 500 ml", "4.80", "3.60", 20, 8),
    ("Lácteos", "Queso fresco Bonlé 500 g", "14.90", "11.50", 8, 3),
    ("Lácteos", "Mantequilla Laive 200 g", "8.50", "6.50", 10, 4),
    # Snacks
    ("Snacks", "Papas Lays clásicas 145 g", "6.50", "4.90", 24, 8),
    ("Snacks", "Chizitos Karinto 40 g", "1.50", "1.00", 60, 20),
    ("Snacks", "Piqueo Snax mixto 130 g", "6.90", "5.20", 15, 6),
    ("Snacks", "Cheese Tris 38 g", "1.50", "1.00", 50, 20),
    ("Snacks", "Maní salado Inka Chips 45 g", "2.50", "1.80", 30, 12),
    ("Snacks", "Doritos queso 145 g", "6.90", "5.20", 18, 8),
    # Golosinas
    ("Golosinas", "Chocolate Sublime clásico 30 g", "2.00", "1.40", 80, 24),
    ("Golosinas", "Chocolate Princesa 32 g", "2.00", "1.40", 65, 24),
    ("Golosinas", "Caramelo Halls mentol", "1.00", "0.65", 100, 30),
    ("Golosinas", "Chupetín Globo Pop", "0.50", "0.30", 120, 40),
    ("Golosinas", "Chocolate Triángulo 36 g", "2.50", "1.80", 40, 15),
    ("Golosinas", "Gomitas Mogul frutas 40 g", "1.50", "1.00", 45, 15),
    # Abarrotes
    ("Abarrotes", "Arroz Costeño extra 5 kg", "26.90", "22.00", 20, 6),
    ("Abarrotes", "Azúcar rubia Cartavio 1 kg", "4.80", "3.80", 30, 10),
    ("Abarrotes", "Aceite Primor 1 L", "9.90", "7.90", 24, 8),
    ("Abarrotes", "Sal de mesa Marina 1 kg", "2.20", "1.50", 25, 8),
    ("Abarrotes", "Lenteja Costeño 500 g", "5.50", "4.30", 18, 6),
    ("Abarrotes", "Ají-no-moto 100 g", "3.50", "2.60", 20, 8),
    # Fideos y pastas
    ("Fideos y pastas", "Spaghetti Don Vittorio 500 g", "4.20", "3.20", 36, 12),
    ("Fideos y pastas", "Tallarín Nicolini 500 g", "3.90", "3.00", 30, 12),
    ("Fideos y pastas", "Fideo cabello de ángel Molitalia 250 g", "2.50", "1.80", 24, 8),
    ("Fideos y pastas", "Sopa instantánea Ajinomen gallina", "1.80", "1.20", 48, 15),
    # Conservas
    ("Conservas", "Atún Florida en aceite 170 g", "6.50", "5.10", 30, 10),
    ("Conservas", "Filete de caballa Campomar 425 g", "7.90", "6.20", 18, 6),
    ("Conservas", "Duraznos en almíbar Aconcagua 820 g", "9.90", "7.80", 10, 4),
    ("Conservas", "Leche condensada Nestlé 393 g", "7.50", "5.90", 15, 6),
    # Panadería
    ("Panadería", "Pan de molde Bimbo blanco 500 g", "7.90", "6.20", 12, 4),
    ("Panadería", "Pan integral Bimbo 500 g", "8.90", "7.00", 8, 4),
    ("Panadería", "Keke de vainilla Bimbo 250 g", "5.50", "4.20", 10, 4),
    ("Panadería", "Tostadas Bimbo 200 g", "6.50", "5.00", 9, 4),
    # Limpieza
    ("Limpieza", "Detergente Bolívar 780 g", "9.50", "7.40", 18, 6),
    ("Limpieza", "Lejía Clorox 1 L", "5.90", "4.50", 15, 6),
    ("Limpieza", "Lavavajilla Sapolio limón 360 g", "5.50", "4.20", 20, 8),
    ("Limpieza", "Papel toalla Elite 2 rollos", "8.90", "7.00", 12, 4),
    ("Limpieza", "Esponja verde multiuso", "2.50", "1.60", 24, 8),
    # Higiene personal
    ("Higiene personal", "Papel higiénico Elite 4 rollos", "8.50", "6.70", 24, 8),
    ("Higiene personal", "Jabón Protex avena 110 g", "4.20", "3.20", 20, 8),
    ("Higiene personal", "Shampoo Head & Shoulders 180 ml", "14.90", "11.80", 8, 3),
    ("Higiene personal", "Pasta dental Colgate 75 ml", "6.90", "5.40", 15, 6),
    ("Higiene personal", "Toallas higiénicas Nosotras 8 unid.", "5.50", "4.30", 12, 5),
]


def _ean13(base12: str) -> str:
    """Completa un EAN-13 con su dígito verificador.

    Los códigos quedan escaneables de verdad, así que sirven para probar el
    lector del POS y no sólo para llenar la columna.
    """
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return base12 + str((10 - suma % 10) % 10)


async def sembrar() -> None:
    try:
        await _sembrar()
    finally:
        # Dentro del mismo loop: hacerlo después de `asyncio.run` intentaría
        # cerrar las conexiones sobre un event loop ya cerrado.
        await engine.dispose()


async def _sembrar() -> None:
    async with SessionLocal() as db:
        admin = (
            await db.execute(select(UsuarioModel).order_by(UsuarioModel.id).limit(1))
        ).scalar_one_or_none()
        if admin is None:
            print("ABORTADO: no hay usuarios. Creá el esquema primero "
                  "(python -m scripts.aplicar_schema).")
            return
        autor = {"creado_por": admin.id, "creado_por_nombre": admin.nombre}

        # --- Categorías -----------------------------------------------------
        por_nombre: dict[str, CategoriaModel] = {}
        nuevas_cat = 0
        for nombre, descripcion in CATEGORIAS:
            cat = (
                await db.execute(
                    select(CategoriaModel).where(
                        CategoriaModel.nombre == nombre,
                        CategoriaModel.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if cat is None:
                cat = CategoriaModel(nombre=nombre, descripcion=descripcion, **autor)
                db.add(cat)
                await db.flush()
                nuevas_cat += 1
            por_nombre[nombre] = cat

        # --- Proveedores ----------------------------------------------------
        nuevos_prov = 0
        for razon_social, ruc, telefono, email, direccion in PROVEEDORES:
            existe = (
                await db.execute(
                    select(ProveedorModel).where(
                        ProveedorModel.ruc == ruc,
                        ProveedorModel.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if existe is None:
                db.add(
                    ProveedorModel(
                        razon_social=razon_social,
                        ruc=ruc,
                        telefono=telefono,
                        email=email,
                        direccion=direccion,
                        activo=True,
                        deuda_actual=Decimal("0"),
                        **autor,
                    )
                )
                nuevos_prov += 1

        # --- Productos ------------------------------------------------------
        nuevos_prod = 0
        for i, (categoria, nombre, precio, compra, stock, minimo) in enumerate(PRODUCTOS):
            codigo = _ean13(f"775{i + 1:09d}")
            existe = (
                await db.execute(
                    select(ProductoModel).where(
                        ProductoModel.codigo == codigo,
                        ProductoModel.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if existe is not None:
                continue
            db.add(
                ProductoModel(
                    codigo=codigo,
                    nombre=nombre,
                    categoria_id=por_nombre[categoria].id,
                    precio=Decimal(precio),
                    precio_compra_actual=Decimal(compra),
                    es_codigo_interno=False,
                    stock=stock,
                    stock_minimo=minimo,
                    activo=True,
                    **autor,
                )
            )
            nuevos_prod += 1

        await db.commit()
        print(f"Categorías creadas : {nuevas_cat:>3} (de {len(CATEGORIAS)})")
        print(f"Proveedores creados: {nuevos_prov:>3} (de {len(PROVEEDORES)})")
        print(f"Productos creados  : {nuevos_prod:>3} (de {len(PRODUCTOS)})")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sembrar())
