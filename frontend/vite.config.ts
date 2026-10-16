import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// App instalable: cada build le pone una versión distinta al service worker
// (public/sw.js trae "__VERSION__"). Así los teléfonos detectan la publicación
// nueva, borran la caché anterior y se actualizan solos, sin reinstalar.
function versionarServiceWorker(): Plugin {
  let salida = "dist";
  return {
    name: "versionar-service-worker",
    apply: "build",
    configResolved(config) {
      salida = path.resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      const sw = path.join(salida, "sw.js");
      const texto = readFileSync(sw, "utf8");
      if (!texto.includes('"__VERSION__"')) throw new Error("No encontré VERSION en dist/sw.js.");
      writeFileSync(sw, texto.replace('"__VERSION__"', JSON.stringify(Date.now().toString(36))));
    },
  };
}

// Configuración mínima de Vite. Cada módulo no debería necesitar tocar este archivo.
export default defineConfig({
  plugins: [react(), versionarServiceWorker()],
});
