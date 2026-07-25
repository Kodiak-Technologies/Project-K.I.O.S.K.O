// Componente para subir una imagen a Storage y mostrar preview + URL final.
// Reutilizado en: GestionProductos (foto del producto), IngresosMercaderia (foto de boleta).
import { useRef, useState, type ChangeEvent } from "react";
import { ImagePlus, Loader2, X } from "lucide-react";
import { useStorage } from "../hooks/useStorage";

interface Props {
  /** Carpeta destino en Storage (`boletas` o `productos`). */
  carpeta: "productos" | "boletas";
  /** URL ya subida (modo edición). */
  value?: string | null;
  /** Callback con la URL firmada devuelta por el backend. */
  onChange: (url: string | null) => void;
  /** Etiqueta visible. */
  label?: string;
  /** Texto de ayuda debajo. */
  ayuda?: string;
  /** Si la subida es obligatoria en validación. */
  requerido?: boolean;
  /** Mensaje de error externo (mostrado abajo). */
  error?: string | null;
}

export function SubirImagen({
  carpeta,
  value,
  onChange,
  label = "Imagen",
  ayuda,
  requerido,
  error,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { subir, subiendo, error: errorStorage, limpiar } = useStorage();
  const [previewLocal, setPreviewLocal] = useState<string | null>(null);

  const urlMostrada = previewLocal ?? value ?? null;

  async function manejarArchivo(e: ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    if (!archivo) return;
    // Preview local inmediato.
    const reader = new FileReader();
    reader.onload = (ev) => setPreviewLocal(ev.target?.result as string);
    reader.readAsDataURL(archivo);
    const resultado = await subir(carpeta, archivo);
    if (resultado) {
      onChange(resultado.url);
      setPreviewLocal(null); // ya tenemos la URL firmada, dejamos de mostrar el data URI.
    } else {
      // Falló la subida: limpiamos el preview.
      setPreviewLocal(null);
    }
    // Reset del input para permitir resubir el mismo archivo.
    if (inputRef.current) inputRef.current.value = "";
  }

  function limpiarImagen() {
    setPreviewLocal(null);
    onChange(null);
    limpiar();
  }

  return (
    <div>
      <span className="mb-1 block text-sm font-medium text-zinc-700">
        {label}
        {requerido && <span className="text-peligro"> *</span>}
      </span>
      {urlMostrada ? (
        <div className="relative inline-block">
          <img
            src={urlMostrada}
            alt="Vista previa"
            className="h-32 w-32 rounded-lg border border-zinc-200 object-cover"
          />
          <button
            type="button"
            onClick={limpiarImagen}
            disabled={subiendo}
            aria-label="Quitar imagen"
            className="absolute -right-2 -top-2 rounded-full bg-white p-1 text-zinc-500 shadow hover:text-peligro disabled:opacity-50"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={subiendo}
          className="flex h-32 w-32 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-zinc-300 text-xs text-zinc-500 hover:border-zinc-400 hover:text-zinc-700 disabled:opacity-50"
        >
          {subiendo ? (
            <Loader2 className="h-6 w-6 animate-spin" aria-hidden />
          ) : (
            <>
              <ImagePlus className="h-6 w-6" aria-hidden />
              <span>Subir imagen</span>
            </>
          )}
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        onChange={(e) => void manejarArchivo(e)}
        className="hidden"
      />
      {ayuda && <p className="mt-1 text-xs text-zinc-500">{ayuda}</p>}
      {(error || errorStorage) && <p className="mt-1 text-xs text-red-700">{error ?? errorStorage}</p>}
    </div>
  );
}
