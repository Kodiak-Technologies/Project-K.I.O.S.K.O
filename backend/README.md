# Backend — Tienda Sistema

FastAPI + arquitectura hexagonal por módulo. Lee primero `../docs/ARQUITECTURA.md`.

## Levantar en local

```bash
python -m venv .venv
.venv/Scripts/activate   # o source .venv/bin/activate en Linux/Mac
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Migraciones (Alembic)

Una sola línea de migraciones compartida por los 4 módulos (ver `docs/ARQUITECTURA.md`).

```bash
alembic revision -m "descripcion"
alembic upgrade head
```

## Tests

```bash
pytest
```

## Estructura

Ver `app/modules/<tu_modulo>/` — cada módulo tiene su propio `domain/`, `application/` e `infrastructure/`.
