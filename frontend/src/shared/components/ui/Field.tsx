// Campos de formulario con label y error integrados. Altura táctil (44px).
import { forwardRef } from "react";
import type { InputHTMLAttributes, SelectHTMLAttributes, ReactNode } from "react";

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
  { label, error, requerido, className = "", ...rest },
  ref
) {
  return (
    <label className="block">
      {label && <Etiqueta texto={label} requerido={requerido} />}
      <input ref={ref} className={`${BASE} ${error ? "border-peligro" : ""} ${className}`} {...rest} />
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
