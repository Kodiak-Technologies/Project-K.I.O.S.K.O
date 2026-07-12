import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configuración mínima de Vite. Cada módulo no debería necesitar tocar este archivo.
export default defineConfig({
  plugins: [react()],
});
