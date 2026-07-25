// Botón del sistema. Primario usa el color de marca configurable (default gris
// casi negro #18181b). Altura mínima táctil de 44px salvo la variante compacta.
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

type Variante = "primario" | "secundario" | "peligro" | "fantasma";

const ESTILOS: Record<Variante, string> = {
  primario: "bg-marca text-white enabled:hover:opacity-85",
  secundario: "border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50",
  peligro: "bg-peligro text-white hover:bg-red-700 disabled:hover:bg-peligro",
  fantasma: "text-zinc-600 hover:bg-zinc-100",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  compacto?: boolean;
  cargando?: boolean;
  icono?: ReactNode;
}

export function Button({
  variante = "primario",
  compacto = false,
  cargando = false,
  icono,
  disabled,
  children,
  className = "",
  ...rest
}: Props) {
  return (
    <button
      disabled={disabled || cargando}
      className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
        compacto ? "px-3 py-1.5 text-sm" : "min-h-tactil px-4 py-2 text-sm"
      } ${ESTILOS[variante]} ${className}`}
      {...rest}
    >
      {cargando ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : icono}
      {children}
    </button>
  );
}
