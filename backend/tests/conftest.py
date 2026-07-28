"""Configuración común a toda la suite.

Los tests unitarios NO tocan la base de datos ni levantan la API: prueban el
dominio (Python puro) y los casos de uso contra dobles en memoria. Por eso
corren en segundos y no necesitan `DATABASE_URL` ni red.

Los end-to-end viven aparte y sí usan la app real.
"""

import asyncio
import sys

import pytest

if sys.platform == "win32":
    # asyncpg y el loop por defecto de Windows no se llevan bien.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
def ahora():
    """Instante fijo, para no depender del reloj en las aserciones."""
    from datetime import datetime, timezone

    return datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)
