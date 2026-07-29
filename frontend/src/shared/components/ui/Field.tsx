import { forwardRef, useState } from "react";
import type { InputHTMLAttributes, SelectHTMLAttributes, ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";

const BASE =
  "w-full min-h-tactil rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 " +
  "placeholder:text-zinc-400 focus:border-zinc-500 disabled:bg-zinc-50 disabled:text-zinc-400";

function Etiqueta({ texto, requerido }: { texto: string; requerido?: boolean }) {
  return (
    <span className="mb-1 block text-sm font-medium text-zinc-700">
      {texto}
      {requerido && <span className="text-peligro"> *</span>}
    </span>
  );
}

function MensajeError({ children }: { children: ReactNode }) {
  return <p className="mt-1 text-xs text-red-700">{children}</p>;
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  requerido?: boolean;
}

// forwardRef: el POS necesita devolver el foco al buscador para el escáner.
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, requerido, className = "", type, ...rest },
  ref
) {
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const esPassword = type === "password";
  const inputType = esPassword ? (mostrarPassword ? "text" : "password") : type;

  return (
    <label className="block">
      {label && <Etiqueta texto={label} requerido={requerido} />}
      <div className="relative">
        <input
          ref={ref}
          type={inputType}
          className={`${BASE} ${esPassword ? "pr-10" : ""} ${error ? "border-peligro" : ""} ${className}`}
          {...rest}
        />
        {esPassword && (
          <button
            type="button"
            onClick={() => setMostrarPassword((prev) => !prev)}
            tabIndex={-1}
            title={mostrarPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            aria-label={mostrarPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-zinc-400 hover:text-zinc-600 focus:outline-none transition-colors"
          >
            {mostrarPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
      {error && <MensajeError>{error}</MensajeError>}
    </label>
  );
});

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string | null;
  requerido?: boolean;
}

export function Select({ label, error, requerido, className = "", children, ...rest }: SelectProps) {
  return (
    <label className="block">
      {label && <Etiqueta texto={label} requerido={requerido} />}
      <select className={`${BASE} ${error ? "border-peligro" : ""} ${className}`} {...rest}>
        {children}
      </select>
      {error && <MensajeError>{error}</MensajeError>}
    </label>
  );
}
