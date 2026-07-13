import type { Config } from "tailwindcss";

// Sistema de diseño K.I.O.S.K.O — base en escala de grises (zinc); el color se
// reserva para ESTADOS (exito/error/alerta/info) y para el acento de marca que
// la dueña configura en runtime (variables CSS que llenan theme-context).
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Acentos configurables desde Configuración (variables CSS en :root).
        marca: "var(--color-primario)",
        "marca-secundario": "var(--color-secundario)",
        // Estados: SIEMPRE fondo suave + texto oscuro en badges/alertas;
        // la versión intensa solo para íconos, puntos y bordes.
        exito: { DEFAULT: "#16a34a", suave: "#dcfce7", intenso: "#22c55e" },
        peligro: { DEFAULT: "#dc2626", suave: "#fee2e2", intenso: "#ef4444" },
        alerta: { DEFAULT: "#a16207", suave: "#fef9c3", intenso: "#eab308" },
        info: { DEFAULT: "#2563eb", suave: "#dbeafe", intenso: "#3b82f6" },
      },
      fontFamily: {
        sans: ["var(--tipografia)", "Inter", "system-ui", "sans-serif"],
      },
      minHeight: {
        // Objetivo táctil mínimo (tablet): botones e ítems de navegación.
        tactil: "2.75rem",
      },
      boxShadow: {
        // Sombra sutil única del sistema: tarjetas y popovers.
        tarjeta: "0 1px 2px 0 rgb(0 0 0 / 0.05), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
      },
    },
  },
  plugins: [],
} satisfies Config;
