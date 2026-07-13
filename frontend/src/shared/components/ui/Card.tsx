// Tarjeta: superficie blanca sobre el fondo zinc-50, borde + sombra sutil.
import type { ReactNode } from "react";

interface Props {
  titulo?: string;
  descripcion?: string;
  accion?: ReactNode;
  sinPadding?: boolean;
  className?: string;
  children: ReactNode;
}

export function Card({ titulo, descripcion, accion, sinPadding = false, className = "", children }: Props) {
  return (
    <section className={`rounded-xl border border-zinc-200 bg-white shadow-tarjeta ${className}`}>
      {(titulo || accion) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-3 sm:px-5">
          <div>
            {titulo && <h3 className="font-semibold text-zinc-900">{titulo}</h3>}
            {descripcion && <p className="text-sm text-zinc-500">{descripcion}</p>}
          </div>
          {accion}
        </header>
      )}
      <div className={sinPadding ? "" : "p-4 sm:p-5"}>{children}</div>
    </section>
  );
}
