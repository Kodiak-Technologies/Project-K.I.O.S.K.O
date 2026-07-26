// Página de historial de notificaciones (stock bajo, apertura/cierre de caja, sistema).
import { useEffect, useState } from "react";
import { Bell, BellOff, CheckCheck, Settings } from "lucide-react";
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
  PaginacionControles,
} from "../../../shared/components/ui";
import { useNotificaciones } from "../hooks/useNotificaciones";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { notificacionesHttpAdapter } from "../services/notificaciones.http-adapter";
import type { TipoNotificacion } from "../types";

const TONO_TIPO: Record<TipoNotificacion, Tono> = {
  STOCK_BAJO: "alerta",
  APERTURA_CAJA: "info",
  CIERRE_CAJA: "info",
  SOLICITUD_INGRESO: "alerta",
  SISTEMA: "neutro",
};

export default function Notificaciones() {
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const { notificaciones, paginados, config, cargando, error, noDisponible, recargar, marcarLeida, actualizarConfig } =
    useNotificaciones();
  const [mostrarConfig, setMostrarConfig] = useState(false);
  const [filtroTipo, setFiltroTipo] = useState<TipoNotificacion | "TODOS">("TODOS");

  // Cambiar de página o de tamaño recarga contra el servidor.
  useEffect(() => {
    void recargar(page, pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  // Auto-marcar todas como leídas al entrar a la página.
  useEffect(() => {
    if (!cargando && !noDisponible && notificaciones.some((n) => !n.leida)) {
      void notificacionesHttpAdapter.marcarTodasLeidas().then(() => void recargar(page, pageSize));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargando, noDisponible]);

  const notificacionesFiltradas = filtroTipo === "TODOS"
    ? notificaciones
    : notificaciones.filter((n) => n.tipo === filtroTipo);

  const marcarTodasLeidas = async () => {
    await notificacionesHttpAdapter.marcarTodasLeidas();
    window.location.reload();
  };

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
        descripcion="Avisos del sistema: stock bajo, apertura y cierre de caja y más."
        acciones={
          <div className="flex gap-2">
            {notificaciones.some((n) => !n.leida) && (
              <Button
                variante="secundario"
                icono={<CheckCheck className="h-4 w-4" aria-hidden />}
                onClick={() => void marcarTodasLeidas()}
              >
                Marcar todas leídas
              </Button>
            )}
            {esAdmin && (
              <Button
                variante="secundario"
                icono={<Settings className="h-4 w-4" aria-hidden />}
                onClick={() => setMostrarConfig(!mostrarConfig)}
              >
                Configuración
              </Button>
            )}
          </div>
        }
      />

      {mostrarConfig && config && (
        <Card titulo="Configuración de notificaciones" className="mb-4">
          <div className="space-y-3">
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
            <p className="text-xs text-zinc-400">
              La configuración de Telegram y correo se realiza en el archivo .env del servidor.
            </p>
          </div>
        </Card>
      )}

      {notificaciones.length > 0 && (
        <div className="mb-4">
          <Select
            label="Filtrar por tipo"
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value as TipoNotificacion | "TODOS")}
          >
            <option value="TODOS">Todos</option>
            <option value="STOCK_BAJO">Stock bajo</option>
            <option value="APERTURA_CAJA">Apertura de caja</option>
            <option value="CIERRE_CAJA">Cierre de caja</option>
            <option value="SOLICITUD_INGRESO">Solicitud de ingreso</option>
            <option value="SISTEMA">Sistema</option>
          </Select>
        </div>
      )}

      {notificacionesFiltradas.length === 0 ? (
        <Card sinPadding>
          <EmptyState icono={BellOff} titulo="Sin notificaciones" descripcion="Todo tranquilo por ahora." />
        </Card>
      ) : (
        <ul className="space-y-2">
          {notificacionesFiltradas.map((n) => (
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

      {/* Misma paginación que el resto de las listas del sistema. */}
      <Card sinPadding className="mt-3">
        <PaginacionControles
          paginados={paginados}
          page={page}
          pageSize={pageSize}
          onCambiarPage={setPage}
          onCambiarPageSize={(n) => {
            setPageSize(n);
            setPage(1);
          }}
          etiqueta="notificaciones"
        />
      </Card>
    </div>
  );
}
