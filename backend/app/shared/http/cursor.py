"""Cursores para paginación por keyset.

Los listados que se ordenan por `created_at DESC, id DESC` reciben filas nuevas
por arriba todo el tiempo (bitácora, movimientos de inventario, solicitudes de
ingreso). Con `LIMIT/OFFSET`, cada request recalcula la posición sobre los datos
del momento: si entra una fila entre la página 1 y la 2, todo se corre un lugar
y el usuario ve una fila repetida; si se borra una, se saltea sin aviso.

El cursor apunta a una **fila concreta** (su `created_at` y su `id`) en vez de a
una posición, así que la consulta pide "lo que viene después de esta fila" y el
resultado no depende de lo que haya pasado más arriba.

El valor es opaco para el cliente a propósito: es base64url de `<iso>|<id>`, y
que sea opaco permite cambiar el formato sin romper a nadie.
"""

import base64
from datetime import datetime

from app.shared.kernel.exceptions import ValidacionError


def codificar_cursor(momento: datetime, id_: int) -> str:
    """Cursor que apunta a la fila (`momento`, `id_`)."""
    crudo = f"{momento.isoformat()}|{id_}".encode()
    return base64.urlsafe_b64encode(crudo).decode().rstrip("=")


def decodificar_cursor(cursor: str) -> tuple[datetime, int]:
    """(momento, id) del cursor. `ValidacionError` si viene corrupto.

    Un cursor inválido es un 422 y no un 500: llega por querystring, así que
    cualquiera puede mandar cualquier cosa.
    """
    try:
        relleno = "=" * (-len(cursor) % 4)
        crudo = base64.urlsafe_b64decode(cursor + relleno).decode()
        iso, _, id_txt = crudo.rpartition("|")
        if not iso:
            raise ValueError("cursor sin separador")
        return datetime.fromisoformat(iso), int(id_txt)
    except ValidacionError:
        raise
    except Exception as exc:  # noqa: BLE001 - cualquier corrupción es lo mismo
        raise ValidacionError(
            "El listado se desactualizó. Vuelve a cargarlo."
        ) from exc
