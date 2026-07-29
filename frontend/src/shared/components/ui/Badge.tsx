import type { ReactNode } from "react";

export type Tono = "exito" | "peligro" | "alerta" | "info" | "neutro";

const ESTILOS: Record<Tono, string> = {
  exito: "bg-exito-suave text-green-800",
  peligro: "bg-peligro-suave text-red-800",
  alerta: "bg-alerta-suave text-yellow-800",
  info: "bg-info-suave text-blue-800",
  neutro: "bg-zinc-100 text-zinc-600",
};

const PUNTO: Record<Tono, string> = {
  exito: "bg-exito-intenso",
  peligro: "bg-peligro-intenso",
  alerta: "bg-alerta-intenso",
  info: "bg-info-intenso",
  neutro: "bg-zinc-400",
};

export function Badge({ tono = "neutro", children }: { tono?: Tono; children: ReactNode }) {
  return (
    <span
      className={`inline-flex max-w-full items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTILOS[tono]}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${PUNTO[tono]}`} aria-hidden />
      <span className="inline-flex items-center gap-1 whitespace-nowrap min-w-0">{children}</span>
    </span>
  );
}
