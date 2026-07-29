import { useEffect, useMemo, useState, type ReactNode } from "react";
import { fileIdDeDrive, httpClient, urlsDeImagen } from "../../lib/http-client";

interface Props {
  src: string | null | undefined;
  alt: string;
  className?: string;
  /** Qué mostrar si no se pudo cargar por ningún camino. */
  respaldo?: ReactNode;
}

export function ImagenConRespaldo({ src, alt, className, respaldo = null }: Props) {
  const candidatas = useMemo(() => urlsDeImagen(src), [src]);
  const fileId = useMemo(() => fileIdDeDrive(src), [src]);
  const [intento, setIntento] = useState(0);
  const [urlDescargada, setUrlDescargada] = useState<string | null>(null);
  const [sinSalida, setSinSalida] = useState(false);

  const clave = candidatas.join("|");

  // Si cambia la imagen (otra fila, otra solicitud) se vuelve a empezar.
  useEffect(() => {
    setIntento(0);
    setUrlDescargada(null);
    setSinSalida(false);
  }, [clave]);

  // Se agotaron las URLs directas: pedirla al backend.
  const agotadas = intento >= candidatas.length;
  useEffect(() => {
    if (!agotadas || !fileId || urlDescargada || sinSalida) return;
    let vigente = true;
    let creada: string | null = null;
    httpClient
      .get(`/storage/boleta/${fileId}`, { responseType: "blob" })
      .then(({ data }) => {
        if (!vigente) return;
        creada = URL.createObjectURL(data as Blob);
        setUrlDescargada(creada);
      })
      .catch(() => vigente && setSinSalida(true));
    return () => {
      vigente = false;
      if (creada) URL.revokeObjectURL(creada);
    };
  }, [agotadas, fileId, urlDescargada, sinSalida]);

  if (candidatas.length === 0) return <>{respaldo}</>;

  if (urlDescargada) {
    return <img src={urlDescargada} alt={alt} className={className} />;
  }

  // Sin candidatas directas que probar y sin descarga posible → mostrar respaldo.
  if (agotadas && (sinSalida || !fileId)) return <>{respaldo}</>;
  // Esperando la descarga del backend o aún cargando URLs directas → respaldo temporal.
  if (agotadas) return <>{respaldo}</>;

  return (
    <img
      key={candidatas[intento]}
      src={candidatas[intento]}
      alt={alt}
      className={className}
      onError={() => setIntento((n) => n + 1)}
    />
  );
}
