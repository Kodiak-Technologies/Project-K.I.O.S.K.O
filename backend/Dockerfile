FROM python:3.11-slim

RUN apt-get update && apt-get install -y libjpeg-dev zlib1g-dev postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# TODO: ajustar host/puerto según configuración final de Cloud Run.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
