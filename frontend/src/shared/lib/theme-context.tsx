// Tema visual global: tema claro por defecto, colores y tipografía configurables.
// Aplica variables CSS (--color-primario, etc.) y persiste la preferencia en
// localStorage; cuando hay sesión, sincroniza con GET /configuracion del backend.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { configuracionHttpAdapter } from "../../modules/modulo-a-seguridad/services/configuracion.http-adapter";

export interface Tema {
  colorPrimario: string;
  colorSecundario: string;
  tipografia: string;
  nombreNegocio: string;
  logoUrl: string;
}

const TEMA_POR_DEFECTO: Tema = {
  colorPrimario: "#2563eb",
  colorSecundario: "#f59e0b",
  tipografia: "Inter",
  nombreNegocio: "Mi Tienda",
  logoUrl: "",
};

const CLAVE_TEMA = "kiosko_tema";

interface TemaContextValue {
  tema: Tema;
  aplicarTema: (cambios: Partial<Tema>) => void;
  sincronizarDesdeBackend: () => Promise<void>;
}

const TemaContext = createContext<TemaContextValue | null>(null);

function aplicarVariablesCss(tema: Tema) {
  const raiz = document.documentElement;
  raiz.style.setProperty("--color-primario", tema.colorPrimario);
  raiz.style.setProperty("--color-secundario", tema.colorSecundario);
  raiz.style.setProperty("--tipografia", tema.tipografia);
  document.body.style.fontFamily = `${tema.tipografia}, system-ui, sans-serif`;
}

export function TemaProvider({ children }: { children: ReactNode }) {
  const [tema, setTema] = useState<Tema>(() => {
    const guardado = localStorage.getItem(CLAVE_TEMA);
    return guardado ? { ...TEMA_POR_DEFECTO, ...JSON.parse(guardado) } : TEMA_POR_DEFECTO;
  });

  useEffect(() => {
    aplicarVariablesCss(tema);
    localStorage.setItem(CLAVE_TEMA, JSON.stringify(tema));
  }, [tema]);

  const aplicarTema = useCallback((cambios: Partial<Tema>) => {
    setTema((actual) => ({ ...actual, ...cambios }));
  }, []);

  const sincronizarDesdeBackend = useCallback(async () => {
    try {
      const config = await configuracionHttpAdapter.obtener();
      setTema({
        colorPrimario: config.color_primario,
        colorSecundario: config.color_secundario,
        tipografia: config.tipografia,
        nombreNegocio: config.nombre_negocio,
        logoUrl: config.logo_url,
      });
    } catch {
      // Sin sesión o sin conexión: se mantiene el tema local.
    }
  }, []);

  return (
    <TemaContext.Provider value={{ tema, aplicarTema, sincronizarDesdeBackend }}>
      {children}
    </TemaContext.Provider>
  );
}

export function useTema(): TemaContextValue {
  const contexto = useContext(TemaContext);
  if (!contexto) throw new Error("useTema debe usarse dentro de <TemaProvider>");
  return contexto;
}
