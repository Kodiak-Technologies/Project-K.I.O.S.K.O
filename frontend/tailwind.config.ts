import type { Config } from "tailwindcss";

// Config mínima. El tema (colores/tipografía configurables) se extiende aquí cuando exista diseño real.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
