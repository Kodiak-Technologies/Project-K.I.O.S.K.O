"""Unit test: the global error handler must surface the `code` field on the
JSON response when an `ErrorDeDominio` is raised with `code=...`.

Per NFR-5 (sdd/modulo-b-aprobaciones-detalle-editar): the response shape is
`{ "detail": "<message>", "code": "<MACHINE_CODE>" }` for domain errors with a
code; for legacy errors (no code), the shape is just `{ "detail": "..." }` —
fully backward compatible.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.http.error_handlers import registrar_error_handlers
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)


def _app_con_endpoint(exc):
    app = FastAPI()
    registrar_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise exc

    return app


def test_conflicto_error_con_code_incluye_code_en_response() -> None:
    app = _app_con_endpoint(ConflictoError("La solicitud ya no se puede editar.", code="NOT_EDITABLE_STATE"))
    client = TestClient(app)
    resp = client.get("/boom")
    assert resp.status_code == 409
    body = resp.json()
    assert body == {"detail": "La solicitud ya no se puede editar.", "code": "NOT_EDITABLE_STATE"}


def test_no_encontrado_error_con_code_devuelve_404_con_code() -> None:
    app = _app_con_endpoint(NoEncontradoError("La solicitud no existe.", code="INGRESO_NOT_FOUND"))
    client = TestClient(app)
    resp = client.get("/boom")
    assert resp.status_code == 404
    body = resp.json()
    assert body == {"detail": "La solicitud no existe.", "code": "INGRESO_NOT_FOUND"}


def test_validacion_error_con_code_devuelve_422_con_code() -> None:
    app = _app_con_endpoint(ValidacionError("No hay cambios para guardar.", code="EMPTY_PATCH"))
    client = TestClient(app)
    resp = client.get("/boom")
    assert resp.status_code == 422
    body = resp.json()
    assert body == {"detail": "No hay cambios para guardar.", "code": "EMPTY_PATCH"}


def test_error_sin_code_respeta_shape_legacy() -> None:
    """Backward compat: error sin code NO agrega el campo `code` (mantiene el shape legacy)."""
    app = _app_con_endpoint(ConflictoError("La solicitud ya fue revisada."))
    client = TestClient(app)
    resp = client.get("/boom")
    assert resp.status_code == 409
    body = resp.json()
    # Solo `detail` (sin `code`)
    assert body == {"detail": "La solicitud ya fue revisada."}
