# Tienda Sistema — Ventas e Inventario

Monorepo con backend (FastAPI, arquitectura hexagonal por módulo) y frontend (React + Vite + TS, organizado por módulo).

Antes de tocar código, lee `docs/ARQUITECTURA.md` (explica cómo está organizado el proyecto y por qué) y `docs/CONVENCIONES.md` (ramas, commits, nombres).

Para el frontend: `docs/FRONTEND_DISENO.md` (sistema de diseño, componentes compartidos y objetivo de cada vista) y `docs/FRONTEND_CONTRATOS_API.md` (endpoints que el frontend espera de los backends B, C y D). Para la base de datos en local: `docs/SCRIPTS_DEV.md` (seed y reset).

## Módulos y responsables

| Módulo | Alcance | Responsable |
|---|---|---|
| A — Seguridad, Accesos, Configuración y Auditoría | `modulo_a_seguridad` | Matías |
| B — Catálogo, Inventario y Aprobación de Ingresos | `modulo_b_inventario` | Brayan |
| C — Ventas, Caja y Punto de Venta (POS) | `modulo_c_ventas` | Clever |
| D — Documentos, Reportes, Notificaciones e Infraestructura | `modulo_d_documentos` | Fabrizio |

## Levantar el proyecto en local

1. Backend: ver `backend/README.md`.
2. Frontend: ver `frontend/README.md`.
3. Alternativamente, `docker-compose up` levanta Postgres local + backend juntos.

## Despliegue

- Backend → Google Cloud Run.
- Base de datos → Google Cloud SQL (PostgreSQL), administrable también desde pgAdmin.
- Frontend → Vercel.
