// Página de historial de notificaciones (stock bajo, cierres de caja, sistema).
import { Bell, BellOff } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  type Tono,
} from "../../../shared/components/ui";
import { useNotificaciones } from "../hooks/useNotificaciones";
import type { TipoNotificacion } from "../types";

const TONO_TIPO: Record<TipoNotificacion, Tono> = {
  STOCK_BAJO: "alerta",
  CIERRE_CAJA: "info",
  SISTEMA: "neutro",
};

export default function Notificaciones() {
  const { notificaciones, cargando, error, noDisponible, marcarLeida } = useNotificaciones();

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Notificaciones" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos (Módulo D)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando notificaciones…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  return (
    <div className="max-w-2xl">
      <PageHeader titulo="Notificaciones" descripcion="Avisos del sistema: stock bajo, cierres de caja y más." />

      {notificaciones.length === 0 ? (
        <Card sinPadding>
          <EmptyState icono={BellOff} titulo="Sin notificaciones" descripcion="Todo tranquilo por ahora." />
        </Card>
      ) : (
        <ul className="space-y-2">
          {notificaciones.map((n) => (
            <li key={n.id}>
              <Card className={n.leida ? "opacity-60" : ""}>
                <div className="flex items-start gap-3">
                  <div className={`rounded-full p-2 ${n.leida ? "bg-zinc-100" : "bg-info-suave"}`}>
                    <Bell className={`h-4 w-4 ${n.leida ? "text-zinc-400" : "text-info"}`} aria-hidden />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-zinc-900">{n.titulo}</p>
                      <Badge tono={TONO_TIPO[n.tipo]}>{n.tipo.replace("_", " ")}</Badge>
                    </div>
                    <p className="mt-0.5 text-sm text-zinc-600">{n.mensaje}</p>
                    <p className="mt-1 text-xs text-zinc-400">
                      {n.created_at ? new Date(n.created_at).toLocaleString("es-PE") : ""}
                    </p>
                  </div>
                  {!n.leida && (
                    <Button variante="secundario" compacto onClick={() => void marcarLeida(n.id)}>
                      Marcar leída
                    </Button>
                  )}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
