// Hook: estado real de la conexión con el backend (HU-C10, RF-26).
// navigator.onLine detecta el cable/wifi, pero el backend puede estar caído
// igual: se confirma con un ping periódico a /health (endpoint público).
import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../../../shared/config/env";

const INTERVALO_PING_MS = 15_000;

export function useConexion() {
  const [online, setOnline] = useState(navigator.onLine);
  const verificando = useRef(false);

  const verificar = useCallback(async () => {
    if (verificando.current) return;
    verificando.current = true;
    try {
      const controlador = new AbortController();
      const temporizador = setTimeout(() => controlador.abort(), 4000);
      const respuesta = await fetch(`${API_BASE_URL}/health`, { signal: controlador.signal });
      clearTimeout(temporizador);
      setOnline(respuesta.ok);
    } catch {
      setOnline(false);
    } finally {
      verificando.current = false;
    }
  }, []);

  useEffect(() => {
    const alConectar = () => void verificar();
    const alDesconectar = () => setOnline(false);
    window.addEventListener("online", alConectar);
    window.addEventListener("offline", alDesconectar);
    void verificar();
    const intervalo = setInterval(() => void verificar(), INTERVALO_PING_MS);
    return () => {
      window.removeEventListener("online", alConectar);
      window.removeEventListener("offline", alDesconectar);
      clearInterval(intervalo);
    };
  }, [verificar]);

  return { online, verificar };
}
