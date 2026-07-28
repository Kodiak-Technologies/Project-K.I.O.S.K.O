FROM python:3.11-slim

RUN apt-get update && apt-get install -y libjpeg-dev zlib1g-dev postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Cloud Run inyecta $PORT (8080 por defecto) y hace el healthcheck en ese puerto.
# Shell form para que ${PORT} se expanda; en local cae a 8080 si no esta definido.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
