// Página de historial de notificaciones (stock bajo, cierres de caja, sistema).
import { useState } from "react";
import { Bell, BellOff, Settings } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
  type Tono,
} from "../../../shared/components/ui";
import { useNotificaciones } from "../hooks/useNotificaciones";
import { useAuthContext } from "../../../shared/lib/auth-context";
import type { TipoNotificacion } from "../types";

const TONO_TIPO: Record<TipoNotificacion, Tono> = {
  STOCK_BAJO: "alerta",
  CIERRE_CAJA: "info",
  SOLICITUD_INGRESO: "alerta",
  SISTEMA: "neutro",
};

export default function Notificaciones() {
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";
  const { notificaciones, config, cargando, error, noDisponible, marcarLeida, actualizarConfig } =
    useNotificaciones();
  const [mostrarConfig, setMostrarConfig] = useState(false);

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
      <PageHeader
        titulo="Notificaciones"
        descripcion="Avisos del sistema: stock bajo, cierres de caja y más."
        acciones={
          esAdmin ? (
            <Button
              variante="secundario"
              icono={<Settings className="h-4 w-4" aria-hidden />}
              onClick={() => setMostrarConfig(!mostrarConfig)}
            >
              Configuración
            </Button>
          ) : undefined
        }
      />

      {mostrarConfig && config && (
        <Card titulo="Configuración de notificaciones" className="mb-4">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="telegram"
                checked={config.canal_telegram_activo}
                onChange={(e) => void actualizarConfig({ canal_telegram_activo: e.target.checked })}
                className="h-4 w-4 rounded border-zinc-300"
              />
              <label htmlFor="telegram" className="text-sm text-zinc-700">
                Telegram
              </label>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="correo"
                checked={config.canal_correo_activo}
                onChange={(e) => void actualizarConfig({ canal_correo_activo: e.target.checked })}
                className="h-4 w-4 rounded border-zinc-300"
              />
              <label htmlFor="correo" className="text-sm text-zinc-700">
                Correo electrónico
              </label>
            </div>
            <Select
              label="Nivel de detalle"
              value={config.nivel_detalle}
              onChange={(e) =>
                void actualizarConfig({ nivel_detalle: e.target.value as "BAJO" | "ALTO" })
              }
            >
              <option value="BAJO">Bajo — Solo aviso</option>
              <option value="ALTO">Alto — Detalle completo</option>
            </Select>
          </div>
        </Card>
      )}

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
                      <Badge tono={TONO_TIPO[n.tipo] ?? "neutro"}>{n.tipo.replace("_", " ")}</Badge>
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
