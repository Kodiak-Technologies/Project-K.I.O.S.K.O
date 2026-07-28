// Aviso que se desvanece solo a los pocos segundos.
//
// Se usa para el feedback del lector de códigos: confirmar que el producto se
// agregó (o avisar que no existe) sin que el mensaje quede colgado en pantalla
// interrumpiendo el escaneo del siguiente.
import { useCallback, useEffect, useRef, useState } from "react";

export type TonoAviso = "exito" | "alerta" | "peligro";

export interface Aviso {
  texto: string;
  tono: TonoAviso;
}

export function useAvisoTemporal(milisegundos = 4000) {
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const temporizador = useRef<number | null>(null);

  const mostrar = useCallback(
    (texto: string, tono: TonoAviso = "exito") => {
      if (temporizador.current !== null) window.clearTimeout(temporizador.current);
      setAviso({ texto, tono });
      temporizador.current = window.setTimeout(() => setAviso(null), milisegundos);
    },
    [milisegundos],
  );

  const limpiar = useCallback(() => {
    if (temporizador.current !== null) window.clearTimeout(temporizador.current);
    setAviso(null);
  }, []);

  // Si el componente se desmonta con un aviso en curso, no dejamos el timer vivo.
  useEffect(() => () => {
    if (temporizador.current !== null) window.clearTimeout(temporizador.current);
  }, []);

  return { aviso, mostrar, limpiar };
}
