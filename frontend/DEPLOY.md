# Despliegue del Frontend — Vercel

Frontend React + Vite del sistema **KIOSKO**. Se despliega en **Vercel** y se conecta al
backend (Cloud Run) mediante la variable `VITE_API_URL`.

- URL del backend en producción: `https://kiosko-backend-ppns2pn4lq-wl.a.run.app`
- El backend debe permitir el origen de Vercel por CORS (ver `backend/DEPLOY.md`, paso 2).

---

## 1. Configuración del proyecto en Vercel

En Vercel → *Add New Project* → importa el repo. Como el front está en subcarpeta, ajusta:

| Campo | Valor |
|---|---|
| Framework Preset | `Vite` |
| Root Directory | `frontend` |
| Build Command | `npm run build`  (default; ejecuta `tsc -b && vite build`) |
| Output Directory | `dist` |
| Install Command | `npm install` |

Los tres comandos son los defaults de Vite: deja los *override* apagados salvo que cambie
el proyecto.

`vercel.json` (ya en el repo) reescribe todas las rutas a `index.html` para el ruteo SPA de
React Router.

---

## 2. Variable de entorno

En Vercel → *Settings* → *Environment Variables*:

| Key | Value | Environments |
|---|---|---|
| `VITE_API_URL` | `https://kiosko-backend-ppns2pn4lq-wl.a.run.app` | Production, Preview |

- **Sin** barra `/` al final (el cliente axios usa esta URL como `baseURL`).
- El archivo `frontend/.env` está en `.gitignore`: es solo para desarrollo local
  (apunta a `http://127.0.0.1:8000`) y **no** se sube al repo ni lo usa Vercel. En Vercel el
  valor viene de esta variable.
- Tras crear o cambiar la variable, haz *Redeploy* para que el build la tome.

---

## 3. Redeploy

Cualquiera de estas opciones:

- **Git:** haz push a la rama conectada (ej. `dev` para Preview, la rama de producción para
  Production). Vercel construye automáticamente.
- **Dashboard:** *Deployments* → menú del último deployment → *Redeploy*.
- **CLI:** desde `frontend/`:

```bash
npm i -g vercel
```

```bash
vercel --prod
```

---

## 4. URLs que genera Vercel

Vercel da tres tipos de URL para el mismo proyecto. Todas deben estar permitidas por el CORS
del backend (hoy se cubren con `CORS_ORIGIN_REGEX`, ver `backend/DEPLOY.md`):

| Tipo | Formato | Cambia |
|---|---|---|
| Producción | `minimarket-<scope>.vercel.app` (o dominio propio) | No |
| Alias de rama | `minimarket-git-<rama>-<scope>.vercel.app` | No |
| Deployment | `minimarket-<hash>-<scope>.vercel.app` | **Sí, en cada deploy** |

---

## 5. Verificación

Tras el deploy, abre la app y prueba el login. Si en la consola del navegador aparece:

- **Error de CORS** (`No 'Access-Control-Allow-Origin'...`): el origen no está permitido en el
  backend → agrégalo en `backend/DEPLOY.md`, paso 2, y redeploya el backend.
- **La petición va a `localhost`**: falta o está mal la variable `VITE_API_URL` en Vercel
  (paso 2) → corrígela y redeploya el front.
