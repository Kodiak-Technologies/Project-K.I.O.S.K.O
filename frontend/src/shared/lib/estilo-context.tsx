// Estilos de interfaz: 6 paletas predefinidas de superficie (fondos, navbar,
// sidebar). No tocan --color-primario ni --color-secundario (esos son la marca).
// Se aplican vía data-estilo en <html> y variables CSS de superficie.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type EstiloId = "claro" | "celeste" | "menta" | "rosa" | "lavanda" | "melocoton";

export interface EstiloUI {
  id: EstiloId;
  nombre: string;
  descripcion: string;
  /** Color de preview del fondo de página */
  previewFondo: string;
  /** Color de preview del sidebar/navbar */
  previewPanel: string;
  /** Acento decorativo */
  previewAccent: string;
}

export const ESTILOS_UI: EstiloUI[] = [
  {
    id: "claro",
    nombre: "Claro",
    descripcion: "Interfaz limpia en blanco y grises suaves",
    previewFondo: "#f4f4f5",
    previewPanel: "#ffffff",
    previewAccent: "#e4e4e7",
  },
  {
    id: "celeste",
    nombre: "Celeste",
    descripcion: "Azul cielo suave, fresco y despejado",
    previewFondo: "#f0f9ff",
    previewPanel: "#e0f2fe",
    previewAccent: "#bae6fd",
  },
  {
    id: "menta",
    nombre: "Menta",
    descripcion: "Fondo verde salvia, relajante y moderno",
    previewFondo: "#f0fdf4",
    previewPanel: "#dcfce7",
    previewAccent: "#bbf7d0",
  },
  {
    id: "rosa",
    nombre: "Rosa",
    descripcion: "Delicado rosa pastel, cálido y elegante",
    previewFondo: "#fff0f6",
    previewPanel: "#fce7f3",
    previewAccent: "#fbcfe8",
  },
  {
    id: "lavanda",
    nombre: "Lavanda",
    descripcion: "Lila suave y sereno, inspirador y creativo",
    previewFondo: "#f5f3ff",
    previewPanel: "#ede9fe",
    previewAccent: "#ddd6fe",
  },
  {
    id: "melocoton",
    nombre: "Melocotón",
    descripcion: "Naranja durazno suave, cálido y acogedor",
    previewFondo: "#fff7ed",
    previewPanel: "#ffedd5",
    previewAccent: "#fed7aa",
  },
];

const CLAVE_ESTILO = "kiosko_estilo_ui";

interface EstiloContextValue {
  estiloActivo: EstiloId;
  setEstilo: (id: EstiloId) => void;
}

const EstiloContext = createContext<EstiloContextValue | null>(null);

function aplicarEstilo(id: EstiloId) {
  document.documentElement.setAttribute("data-estilo", id);
}

export function EstiloProvider({ children }: { children: ReactNode }) {
  const [estiloActivo, setEstiloActivo] = useState<EstiloId>(() => {
    const guardado = localStorage.getItem(CLAVE_ESTILO) as EstiloId | null;
    return guardado && ESTILOS_UI.some((e) => e.id === guardado) ? guardado : "claro";
  });

  useEffect(() => {
    aplicarEstilo(estiloActivo);
    localStorage.setItem(CLAVE_ESTILO, estiloActivo);
  }, [estiloActivo]);

  const setEstilo = useCallback((id: EstiloId) => setEstiloActivo(id), []);

  return (
    <EstiloContext.Provider value={{ estiloActivo, setEstilo }}>
      {children}
    </EstiloContext.Provider>
  );
}

export function useEstiloUI(): EstiloContextValue {
  const ctx = useContext(EstiloContext);
  if (!ctx) throw new Error("useEstiloUI debe usarse dentro de <EstiloProvider>");
  return ctx;
}
