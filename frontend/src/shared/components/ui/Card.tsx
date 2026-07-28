import type { ReactNode } from "react";

interface Props {
  titulo?: string;
  descripcion?: string;
  accion?: ReactNode;
  sinPadding?: boolean;
  className?: string;
  cuerpoClassName?: string;
  children: ReactNode;
}

export function Card({ titulo, descripcion, accion, sinPadding = false, className = "", cuerpoClassName = "", children }: Props) {
  return (
    <section className={`rounded-xl border border-zinc-200 bg-white shadow-tarjeta w-full max-w-full min-w-0 ${className}`}>
      {(titulo || accion) && (
        // shrink-0: si la tarjeta se usa como columna flex, el alto sobrante va
        // al cuerpo, no achica el encabezado.
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-3 sm:px-5">
          <div>
            {titulo && <h3 className="font-semibold text-zinc-900">{titulo}</h3>}
            {descripcion && <p className="text-sm text-zinc-500">{descripcion}</p>}
          </div>
          {accion}
        </header>
      )}
      <div className={`${sinPadding ? "" : "p-4 sm:p-5"} w-full max-w-full min-w-0 ${cuerpoClassName}`}>{children}</div>
    </section>
  );
}
