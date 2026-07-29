# Vacía los datos del negocio y vuelve a dejar el baseline mínimo.
#
# Para qué sirve: volver a cero después de probar. Borra ventas, turnos,
# productos, ingresos, proveedores, movimientos, bitácora, usuarios… Después
# corre el seed, así que al terminar podés entrar y operar como el primer día.
#
# QUÉ SOBREVIVE, y por qué: no todo lo que hay en la base es "dato de prueba".
# Hay tablas que son configuración del sistema, y borrarlas obliga a rehacer a
# mano un trabajo que no tiene nada que ver con los datos que se quieren tirar:
#
#   - `alembic_version`  Control de migraciones, no un dato del negocio. Si se
#                        borrara, Alembic creería que la base nunca se migró.
#                        No se toca nunca, ni con --borrar-configuracion.
#   - `metodos_pago`     Sin métodos activos el POS no puede cobrar, y hoy no
#                        hay pantalla para darlos de alta.
#   - `oauth_tokens`     La autorización de Google Drive. Rehacerla es un
#                        trámite manual en el navegador.
#
# Con --borrar-configuracion se borran también los dos últimos, para dejar la
# base igual que en una instalación nueva.
#
# La lista de tablas se lee de la base, no está escrita acá: si mañana el
# esquema suma una tabla, este script la vacía sin que nadie se acuerde de
# actualizarlo.
#
# TRUNCATE no dispara el trigger de fila `trg_bitacora_inmutable`, así que la
# bitácora sigue siendo inmutable para la aplicación; este script es la única
# puerta de borrado y por eso se niega a correr fuera de un entorno local.
#
# Uso:
#   python -m scripts.reset_db                          # pide confirmación
#   python -m scripts.reset_db --si                     # sin preguntar
#   python -m scripts.reset_db --borrar-configuracion   # también métodos de pago y Drive
#   python -m scripts.reset_db --sin-seed               # deja la base vacía del todo
import argparse
import asyncio
import sys

from sqlalchemy import text

from app.shared.config.settings import settings
from app.shared.database.session import engine
from scripts.seed import seed

# Nunca se borra, bajo ninguna opción.
CONSERVAR_SIEMPRE = {"alembic_version"}

# Configuración del sistema: sobrevive salvo que se pida --borrar-configuracion.
CONSERVAR_POR_DEFECTO = {"metodos_pago", "oauth_tokens"}


async def _tablas_a_vaciar(conn, borrar_configuracion: bool) -> tuple[list[str], list[str]]:
    """Devuelve (a_vaciar, conservadas), leyendo las tablas reales de la base."""
    filas = await conn.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    )
    todas = [t for (t,) in filas]

    conservadas = set(CONSERVAR_SIEMPRE)
    if not borrar_configuracion:
        conservadas |= CONSERVAR_POR_DEFECTO

    a_vaciar = [t for t in todas if t not in conservadas]
    return a_vaciar, [t for t in todas if t in conservadas]


async def reset(confirmado: bool, borrar_configuracion: bool, sin_seed: bool) -> None:
    if settings.environment != "local":
        print(f"ERROR: entorno '{settings.environment}' — este script solo corre en 'local'.")
        sys.exit(1)

    async with engine.begin() as conn:
        a_vaciar, conservadas = await _tablas_a_vaciar(conn, borrar_configuracion)
        if not a_vaciar:
            print("No hay tablas para vaciar. ¿Aplicaste el esquema? (python -m scripts.aplicar_schema)")
            sys.exit(1)

        if not confirmado:
            print(f"Base: {settings.database_url}\n")
            print(f"Se VACÍAN {len(a_vaciar)} tablas:\n  {', '.join(a_vaciar)}\n")
            print(f"Se CONSERVAN {len(conservadas)}:\n  {', '.join(conservadas)}\n")
            if input("Escribe BORRAR para continuar: ").strip() != "BORRAR":
                print("Cancelado. No se tocó nada.")
                sys.exit(0)

        # Todas juntas en un TRUNCATE: CASCADE resuelve las claves foráneas sin
        # tener que ordenarlas a mano, y RESTART IDENTITY devuelve los
        # autoincrementales a 1 para que la base quede como recién creada.
        #
        # Conservar `metodos_pago` es seguro: CASCADE arrastra de la tabla padre
        # a sus hijas, y acá es al revés — la que se borra es `pagos_venta`, que
        # es la que apunta a `metodos_pago`, no al revés.
        await conn.execute(
            text(f"TRUNCATE TABLE {', '.join(a_vaciar)} RESTART IDENTITY CASCADE")
        )

    print(f"Vaciadas {len(a_vaciar)} tablas. Conservadas: {', '.join(conservadas)}.")

    if sin_seed:
        print("Base sin sembrar (--sin-seed). Para poder entrar, corre: python -m scripts.seed")
        await engine.dispose()
        return

    # seed() hace engine.dispose() al final, así que no hace falta repetirlo acá.
    await seed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Vacía los datos del negocio y vuelve a sembrar el baseline mínimo."
    )
    parser.add_argument("--si", action="store_true", help="No pedir confirmación.")
    parser.add_argument(
        "--borrar-configuracion",
        action="store_true",
        help="Borrar también métodos de pago y la autorización de Google Drive.",
    )
    parser.add_argument("--sin-seed", action="store_true", help="Dejar la base vacía, sin sembrar.")
    args = parser.parse_args()

    asyncio.run(reset(args.si, args.borrar_configuracion, args.sin_seed))
