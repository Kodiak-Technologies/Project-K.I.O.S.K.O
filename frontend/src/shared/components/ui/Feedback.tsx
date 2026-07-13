// Piezas de feedback: alertas, estado vacío, spinner de página y encabezado.
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, Info, Loader2, Unplug, XCircle } from "lucide-react";

type TonoAlerta = "exito" | "peligro" | "alerta" | "info";

const ALERTA: Record<TonoAlerta, { clases: string; Icono: LucideIcon }> = {
  exito: { clases: "bg-exito-suave text-green-800", Icono: CheckCircle2 },
  peligro: { clases: "bg-peligro-suave text-red-800", Icono: XCircle },
  alerta: { clases: "bg-alerta-suave text-yellow-800", Icono: AlertTriangle },
  info: { clases: "bg-info-suave text-blue-800", Icono: Info },
};

export function Alert({ tono, children }: { tono: TonoAlerta; children: ReactNode }) {
  const { clases, Icono } = ALERTA[tono];
  return (
    <div role="alert" className={`flex items-start gap-2 rounded-lg px-3 py-2.5 text-sm ${clases}`}>
      <Icono className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}

interface EmptyStateProps {
  icono: LucideIcon;
  titulo: string;
  descripcion?: string;
  accion?: ReactNode;
}

export function EmptyState({ icono: Icono, titulo, descripcion, accion }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center">
      <div className="rounded-full bg-zinc-100 p-3">
        <Icono className="h-6 w-6 text-zinc-400" aria-hidden />
      </div>
      <p className="font-medium text-zinc-700">{titulo}</p>
      {descripcion && <p className="max-w-sm text-sm text-zinc-500">{descripcion}</p>}
      {accion && <div className="mt-2">{accion}</div>}
    </div>
  );
}

/** Pantalla para módulos cuyo backend aún no está desplegado (B, C, D). */
export function ModuloPendiente({ modulo }: { modulo: string }) {
  return (
    <EmptyState
      icono={Unplug}
      titulo="Módulo aún no conectado"
      descripcion={`La interfaz está lista, pero el backend de ${modulo} todavía no está disponible. Cuando el equipo publique sus endpoints, esta pantalla funcionará sola.`}
    />
  );
}

/** Spinner centrado para la carga inicial de una página. */
export function PageSpinner({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-zinc-500">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      <span className="text-sm">{texto}</span>
    </div>
  );
}

interface PageHeaderProps {
  titulo: string;
  descripcion?: string;
  acciones?: ReactNode;
}

export function PageHeader({ titulo, descripcion, acciones }: PageHeaderProps) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-xl font-semibold text-zinc-900">{titulo}</h2>
        {descripcion && <p className="mt-0.5 text-sm text-zinc-500">{descripcion}</p>}
      </div>
      {acciones && <div className="flex items-center gap-2">{acciones}</div>}
    </div>
  );
}
