# Despliegue del Backend — Google Cloud Run

Backend FastAPI del sistema **KIOSKO**. Se construye con **Cloud Build**, la imagen se
guarda en **Artifact Registry** y corre en **Cloud Run**. La base de datos es **Supabase**
(conexión directa por `asyncpg`; **no** usa Cloud SQL).

> ⚠️ **Nunca** pongas valores de secretos (password de la BD, `SECRET_KEY`, tokens, `SMTP_PASS`)
> en este archivo ni en `cloudbuild.yaml`. Los secretos viven en **Secret Manager** y en tu
> `.env` local (que está en `.gitignore` y no se sube a GitHub).

---

## Datos del entorno

| Recurso | Valor |
|---|---|
| Proyecto GCP | `project-e4ebe808-25e7-4d10-844` |
| Región | `us-west2` |
| Servicio Cloud Run | `kiosko-backend` |
| Repo Artifact Registry | `kiosko` (formato Docker) |
| Secretos (Secret Manager) | `kiosko-database-url`, `kiosko-secret-key` |
| Service Account del build | `1049232196871-compute@developer.gserviceaccount.com` |
| URL pública | https://kiosko-backend-1049232196871.us-west2.run.app |

> La **cuenta** que despliega debe tener permisos de owner/editor en el proyecto
> (se usó `kodiak.technologies.team@gmail.com`).

---

## 1. Redeploy (el caso más común)

Cada vez que cambias código del backend y quieres publicarlo. La infraestructura
(repo, secretos, permisos, servicio) **ya existe**, así que es un solo comando.

```bash
gcloud config set project project-e4ebe808-25e7-4d10-844
```

```bash
cd backend
gcloud builds submit --config=cloudbuild.yaml .
```

Eso construye la imagen, la sube y actualiza el servicio Cloud Run con la nueva versión.
Sube el código de tu **working directory** (no necesita commit previo).

Al terminar, verifica:

```bash
curl https://kiosko-backend-1049232196871.us-west2.run.app/health
```

Debe responder `{"status":"ok"}`.

---

## 2. Orígenes de CORS

El backend acepta orígenes de dos fuentes, ambas en el `--set-env-vars` de `cloudbuild.yaml`:

- `CORS_ORIGINS` (substitución `_CORS_ORIGINS`): lista de orígenes fijos separados por coma,
  **sin espacios**. Aquí van `localhost` y cualquier dominio propio.
- `CORS_ORIGIN_REGEX`: patrón que acepta todos los subdominios de Vercel del proyecto. Se usa
  porque la URL de *deployment* de Vercel cambia en cada deploy (`minimarket-<hash>-...`).
  Valor actual: `https://minimarket-[a-z0-9-]+\.vercel\.app`

Para cambiarlos, edita esas líneas en `cloudbuild.yaml` y haz el redeploy del paso 1.

El valor de `_CORS_ORIGINS` lleva comas, por eso `cloudbuild.yaml` usa el delimitador `^@@^`
en `--set-env-vars` (si no, gcloud parte el valor por la coma). Para pasarlo por línea de
comando sin editar el archivo:

```bash
gcloud builds submit --config=cloudbuild.yaml "--substitutions=^@@^_CORS_ORIGINS=http://localhost:5173,http://localhost:5174" .
```

---

## 3. Crear o actualizar un secreto

Los valores de `DATABASE_URL` y `SECRET_KEY` viven en Secret Manager. Para cambiarlos
(ej. rotar la clave o cambiar la BD) **sin dejar el valor en el historial** y **sin salto de
línea final** (un `\n` extra rompe la connection string), en PowerShell:

```powershell
"PEGA_AQUI_EL_VALOR" | Out-File -NoNewline -Encoding ascii "$env:TEMP\secret.txt"
gcloud secrets versions add kiosko-database-url --data-file="$env:TEMP\secret.txt"
Remove-Item "$env:TEMP\secret.txt"
```

Cambia `kiosko-database-url` por `kiosko-secret-key` según corresponda.

Agregar una versión del secreto **no** actualiza el servicio en ejecución: hay que rodar una
revisión nueva. Para aplicar solo el cambio de secreto sin reconstruir la imagen:

```bash
gcloud run services update kiosko-backend --region=us-west2 --update-secrets=DATABASE_URL=kiosko-database-url:latest
```

Para `kiosko-secret-key` es igual, cambiando el par: `--update-secrets=SECRET_KEY=kiosko-secret-key:latest`.
(El redeploy completo del paso 1 también toma la versión `:latest`.)

> **Módulo D** (Drive/Telegram/SMTP) usa más variables (ver `.env.example`). Hoy **no** se
> inyectan en producción. Si se necesitan, créalas como secretos y agrégalas al
> `--set-secrets` del `cloudbuild.yaml` con el mismo patrón. Nunca las pongas en texto plano.

---

## 4. Setup inicial desde cero (solo para un proyecto GCP nuevo)

Si algún día se monta en otro proyecto GCP. En el proyecto actual **esto ya está hecho**.

```bash
gcloud auth login
```

```bash
gcloud config set project TU_PROJECT_ID
```

Habilitar APIs:

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

Crear el repo de imágenes:

```bash
gcloud artifacts repositories create kiosko --repository-format=docker --location=us-west2 --description="Docker KIOSKO Backend"
```

Crear los secretos (vacíos) y luego cargar sus valores con el método del paso 3:

```bash
gcloud secrets create kiosko-database-url --replication-policy="automatic"
```

```bash
gcloud secrets create kiosko-secret-key --replication-policy="automatic"
```

**Permisos IMPORTANTES** — el build corre como la *compute service account*
(`PROJECT_NUMBER-compute@developer.gserviceaccount.com`), **no** la `@cloudbuild...`.
A ESA cuenta hay que darle los roles (reemplaza `PROJECT_NUMBER` y `PROJECT_ID`):

```bash
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/logging.logWriter"
```

```bash
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/artifactregistry.writer"
```

```bash
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/run.admin"
```

```bash
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

```bash
gcloud iam service-accounts add-iam-policy-binding PROJECT_NUMBER-compute@developer.gserviceaccount.com --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/iam.serviceAccountUser"
```

Después, el primer deploy es igual que el redeploy (paso 1).

---

## 5. Verificación y troubleshooting

Ver la URL del servicio:

```bash
gcloud run services describe kiosko-backend --region=us-west2 --format="value(status.url)"
```

Ver logs del último build (usa el BUILD_ID que imprime `submit`):

```bash
gcloud builds log BUILD_ID
```

Ver logs del servicio en ejecución (errores y tracebacks):

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="kiosko-backend" AND severity>=WARNING' --limit=40 --freshness=1h --format="value(timestamp,textPayload)"
```

**Errores ya vistos y su causa:**

| Síntoma | Causa | Solución |
|---|---|---|
| `docker ... exited with non-zero status: 125` | Tag inválido por `$SHORT_SHA` vacío en submit manual | Usar `$BUILD_ID` (ya aplicado) |
| `... does not have storage.objects.get` / `permission to write logs` | Roles puestos en la SA equivocada | Dárselos a la **compute SA** (paso 4) |
| Deploy falla en healthcheck / "container failed to listen on PORT" | Dockerfile con puerto fijo `8000` | `CMD` usa `${PORT:-8080}` (ya aplicado) |
| `Bad syntax for dict arg` con la coma de CORS | gcloud parte el valor por la coma | Usar el delimitador `^@@^` (ver paso 2) |
| El front en Vercel da error de CORS | El origen no está en `CORS_ORIGINS` ni matchea `CORS_ORIGIN_REGEX` | Agregarlo y redeployar (paso 2) |
| `500` en endpoints que usan BD; log `asyncpg.exceptions.InvalidCatalogNameError: database "postgres\n"` | Salto de línea `\n` al final del secreto `DATABASE_URL` (creado con `echo`/`Out-File` sin `-NoNewline`) | Recrear el secreto sin newline (paso 3) y rodar revisión nueva. Nota: `/health` **no** detecta esto porque no toca BD |

---

## 6. Archivos de despliegue

| Archivo | Para qué |
|---|---|
| `cloudbuild.yaml` | Define los 3 pasos: build → push → deploy |
| `Dockerfile` | Imagen Python 3.11 + FastAPI; escucha en `$PORT` |
| `.gcloudignore` | Qué **no** sube `gcloud builds submit` (evita `.venv`, `.env`, credenciales) |
| `.dockerignore` | Qué **no** entra en la imagen (`COPY . .`) |

`.env`, `.env.*` y `*-credentials.json` están en `.gitignore` y en los dos `.ignore`:
**nunca** salen del equipo ni entran a la imagen. En producción esos valores llegan por
`--set-secrets` y `--set-env-vars` (ver `cloudbuild.yaml`).
