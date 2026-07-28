import { useRef, useState, type ChangeEvent } from "react";
import { CheckCircle2, ImagePlus, Loader2, X } from "lucide-react";
import { normalizarImagenUrl } from "../../../shared/lib/http-client";
import { useStorage } from "../hooks/useStorage";

interface Props {
  carpeta: "boletas";
  value?: string | null;
  onChange: (url: string | null) => void;
  label?: string;
  ayuda?: string;
  requerido?: boolean;
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

  const [errorLocal, setErrorLocal] = useState<string | null>(null);

  const urlMostrada = previewLocal ?? value ?? null;

  async function manejarArchivo(e: ChangeEvent<HTMLInputElement>) {
    setErrorLocal(null);
    const archivo = e.target.files?.[0];
    if (!archivo) return;

    const mime = archivo.type.toLowerCase();
    const ext = "." + (archivo.name.split(".").pop()?.toLowerCase() ?? "");

    const mimesValidos = ["image/jpeg", "image/png", "image/jpg"];
    const extsValidas = [".jpg", ".jpeg", ".png"];

    if (!mimesValidos.includes(mime) && !extsValidas.includes(ext)) {
      setErrorLocal("Solo se permiten archivos de imagen en formato JPG o PNG.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => setPreviewLocal(ev.target?.result as string);
    reader.readAsDataURL(archivo);
    const resultado = await subir(carpeta, archivo);
    if (resultado) {
      onChange(resultado.url);
      setPreviewLocal(null);
    } else {
      setPreviewLocal(null);
    }
    if (inputRef.current) inputRef.current.value = "";
  }

  function limpiarImagen() {
    setErrorLocal(null);
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
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-zinc-200 bg-zinc-50 p-2.5">
          <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg border border-zinc-200 bg-white">
            <img
              src={normalizarImagenUrl(urlMostrada)}
              alt="Vista previa boleta"
              className="h-full w-full object-cover"
            />
          </div>
          <div className="flex min-w-0 flex-1 flex-col justify-center gap-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-green-700">
              <CheckCircle2 className="h-4 w-4 text-exito-intenso" />
              <span>Foto de boleta adjuntada</span>
            </div>
            <p className="text-xs text-zinc-500">Se guardará junto con la solicitud de ingreso.</p>
            <div className="mt-1 flex items-center gap-2">
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                disabled={subiendo}
                className="text-xs font-medium text-zinc-700 underline hover:text-zinc-900 disabled:opacity-50"
              >
                Cambiar foto
              </button>
              <button
                type="button"
                onClick={limpiarImagen}
                disabled={subiendo}
                className="inline-flex items-center gap-1 text-xs font-medium text-peligro hover:underline disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" /> Eliminar
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={subiendo}
          className="flex min-h-tactil w-full sm:w-auto items-center justify-center gap-2 rounded-lg border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-800 shadow-sm transition hover:border-zinc-400 hover:bg-zinc-50 focus:outline-none focus:ring-1 focus:ring-zinc-500 disabled:opacity-50"
        >
          {subiendo ? (
            <Loader2 className="h-4 w-4 animate-spin text-zinc-500" aria-hidden />
          ) : (
            <ImagePlus className="h-4 w-4 text-zinc-500" aria-hidden />
          )}
          <span>{subiendo ? "Subiendo foto de boleta…" : "Adjuntar foto de la boleta"}</span>
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,.jpg,.jpeg,.png"
        onChange={(e) => void manejarArchivo(e)}
        className="hidden"
      />
      {ayuda && <p className="mt-1 text-xs text-zinc-500">{ayuda}</p>}
      {(error || errorStorage || errorLocal) && (
        <p className="mt-1 text-xs font-medium text-peligro">{errorLocal ?? error ?? errorStorage}</p>
      )}
    </div>
  );
}
