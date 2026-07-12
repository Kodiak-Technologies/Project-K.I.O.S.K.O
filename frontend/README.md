# Frontend — Tienda Sistema

React + Vite + TypeScript, organizado por módulo/feature (no hexagonal — ver `../docs/ARQUITECTURA.md` §6).

## Levantar en local

```bash
npm install
cp .env.example .env
npm run dev
```

## Estructura

Ver `src/modules/<tu-modulo>/` — cada módulo tiene `components/`, `pages/`, `hooks/`, `services/` (puerto + adaptador HTTP) y `types/`.
