# Guía de despliegue paso a paso — Project K.I.O.S.K.O

Cómo llevar TODO a producción: PostgreSQL en **Cloud SQL**, backend en **Cloud Run**, frontend en **Vercel**, y cómo probarlo desplegado. Sigue las secciones en orden.

> Prerequisito: instala Google Cloud CLI (`gcloud`) desde https://cloud.google.com/sdk/docs/install y ejecuta `gcloud auth login` y `gcloud config set project TU_PROYECTO`.

---

## 1. Base de datos — Cloud SQL (PostgreSQL)

### 1.1 Crear la instancia

```bash
gcloud sql instances create kiosko-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB \
  --backup-start-time=06:00
```

(También puedes hacerlo desde la consola web: SQL → Crear instancia → PostgreSQL, preajuste Sandbox.)

### 1.2 Crear base de datos y usuarios

```bash
gcloud sql databases create tienda_sistema --instance=kiosko-db
gcloud sql users create app_kiosko --instance=kiosko-db --password=PASSWORD_APP_SEGURA
gcloud sql users create lectura_pgadmin --instance=kiosko-db --password=PASSWORD_LECTURA
```

### 1.3 Aplicar migraciones y seed (desde tu PC, vía Cloud SQL Auth Proxy)

1. Descarga el proxy: https://cloud.google.com/sql/docs/postgres/sql-proxy (ejecutable, sin instalación).
2. En una terminal: `cloud-sql-proxy TU_PROYECTO:us-central1:kiosko-db --port 5433`
3. En otra terminal, dentro de `backend/`:

```bash
# apuntar temporalmente el .env al proxy:
# DATABASE_URL=postgresql+asyncpg://app_kiosko:PASSWORD_APP_SEGURA@localhost:5433/tienda_sistema
.venv/Scripts/python -m alembic upgrade head
ADMIN_USERNAME=admin ADMIN_PASSWORD=UnaClaveSegura1 .venv/Scripts/python -m scripts.seed
```

4. Ejecuta además los `GRANT`/`REVOKE` de `backend/db/schema_modulo_a.sql` (sección 4) conectado como `postgres`, para que `app_kiosko` no pueda tocar la bitácora y `lectura_pgadmin` sea solo lectura.

### 1.4 Conectarse con pgAdmin — dos opciones

**Opción A — Cloud SQL Auth Proxy (RECOMENDADA):** deja el proxy corriendo (paso 1.3) y en pgAdmin crea un servidor con host `localhost`, puerto `5433`, usuario `lectura_pgadmin`. Ventajas: no expones la BD a internet, el tráfico va cifrado y autenticado con tu cuenta de Google. Desventaja: debes tener el proxy abierto mientras consultas.

**Opción B — IP autorizada:** en la consola → SQL → kiosko-db → Conexiones → Redes autorizadas, agrega tu IP pública (la ves en https://ifconfig.me) como `TU_IP/32`. Luego en pgAdmin usa la IP pública de la instancia, puerto 5432. Ventaja: sin proxy. Desventajas: tu IP de casa cambia (tendrás que re-autorizarla) y la BD queda expuesta a internet aunque protegida por contraseña. Úsala solo si el proxy te resulta incómodo.

### 1.5 Backups y exportación (por si migras de cuenta de Google Cloud)

- **Automáticos + PITR** (ya activados con `--backup-start-time`; verifica en consola → SQL → kiosko-db → Backups, y habilita "Point-in-time recovery").
- **Respaldo manual descargable** (formato custom, restaurable en cualquier Postgres):

```bash
# con el proxy corriendo en 5433:
pg_dump -Fc -h localhost -p 5433 -U postgres -d tienda_sistema -f respaldo_kiosko.dump
# restaurar en otra instancia/cuenta:
pg_restore -h localhost -p 5433 -U postgres -d tienda_sistema --clean respaldo_kiosko.dump
```

---

## 2. Backend — Cloud Run

### 2.1 Secretos en Secret Manager (nunca en el repo)

```bash
# URL de BD usando el socket Unix de Cloud SQL (nota el host vacío y ?host=):
echo -n "postgresql+asyncpg://app_kiosko:PASSWORD_APP_SEGURA@/tienda_sistema?host=/cloudsql/TU_PROYECTO:us-central1:kiosko-db" | \
  gcloud secrets create kiosko-database-url --data-file=-

# clave de firma de JWT (genera una aleatoria):
python -c "import secrets; print(secrets.token_urlsafe(48))" | gcloud secrets create kiosko-secret-key --data-file=-
```

### 2.2 Desplegar

```bash
gcloud artifacts repositories create kiosko --repository-format=docker --location=us-central1
cd backend
gcloud builds submit --config cloudbuild.yaml .
```

`cloudbuild.yaml` construye la imagen, la sube y despliega `kiosko-backend` con `--add-cloudsql-instances` (conexión por socket Unix: la BD **no** expone IP pública al backend). Edita la sustitución `_CORS_ORIGINS` con tu dominio real de Vercel.

### 2.3 Probar el backend desplegado

```bash
# URL del servicio:
gcloud run services describe kiosko-backend --region us-central1 --format="value(status.url)"

curl https://kiosko-backend-XXXX.run.app/health          # -> {"status":"ok"}
curl -X POST https://kiosko-backend-XXXX.run.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"UnaClaveSegura1"}'  # -> tokens
```

También puedes abrir `https://.../docs` (Swagger) y probar todos los endpoints desde el navegador.

---

## 3. Frontend — Vercel

1. Sube el repo a GitHub (si aún no).
2. En https://vercel.com → **Add New Project** → importa el repo.
3. **Root Directory**: `frontend` (importante, es un monorepo).
4. Framework preset: **Vite** (lo detecta solo).
5. En **Environment Variables** agrega: `VITE_API_URL = https://kiosko-backend-XXXX.run.app` (la URL de Cloud Run del paso 2.3).
6. Deploy. Vercel te da `https://tu-proyecto.vercel.app`.
7. **Vuelve al backend** y actualiza CORS con ese dominio:

```bash
gcloud run services update kiosko-backend --region us-central1 \
  --set-env-vars=CORS_ORIGINS=https://tu-proyecto.vercel.app
```

---

## 4. Prueba de punta a punta (todo desplegado)

1. Abre `https://tu-proyecto.vercel.app` **desde tu celular** (la app es responsive desde 360 px).
2. Inicia sesión con `admin` / la contraseña del seed. Verifica que NO exista opción "Crear cuenta".
3. En **Usuarios**, crea `vendedor1` (rol CAJERO) con una contraseña inicial.
4. Cierra sesión, falla el login de `vendedor1` 3 veces → al 4.º intento (aunque sea correcto) debe responder "Cuenta bloqueada temporalmente".
5. Entra como `admin` → **Bitácora** → filtra por acción `cuenta_bloqueada`: debe aparecer el evento con IP y fecha.
6. En **Configuración**, cambia color primario y nombre del negocio → la barra superior cambia al instante y el cambio queda auditado.
7. Cierra la app del celular, ábrela horas después: la sesión del ADMIN sigue viva (refresh token de 30 días).
8. En pgAdmin (sección 1.4) intenta `UPDATE bitacora_auditoria SET rol='x';` → debe fallar con "La bitácora de auditoría es inmutable".

---

## 5. Resumen de variables de entorno

| Dónde | Variable | Valor |
|---|---|---|
| Cloud Run (secreto) | `DATABASE_URL` | `postgresql+asyncpg://app_kiosko:...@/tienda_sistema?host=/cloudsql/...` |
| Cloud Run (secreto) | `SECRET_KEY` | cadena aleatoria larga (firma JWT) |
| Cloud Run | `CORS_ORIGINS` | `https://tu-proyecto.vercel.app` |
| Cloud Run | `ENVIRONMENT` | `production` |
| Seed (una vez) | `ADMIN_USERNAME` / `ADMIN_PASSWORD` | credenciales del ADMIN inicial |
| Vercel | `VITE_API_URL` | URL del servicio de Cloud Run |
