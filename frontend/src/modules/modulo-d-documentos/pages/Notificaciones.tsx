import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, BellOff, CheckCheck, ExternalLink, Settings } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
  type Tono,
  PaginacionControles,
} from "../../../shared/components/ui";
import { useNotificaciones } from "../hooks/useNotificaciones";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { useAltoDisponible } from "../../../shared/lib/use-alto-disponible";
import { notificacionesHttpAdapter } from "../services/notificaciones.http-adapter";
import type { Notificacion, TipoNotificacion } from "../types";

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
  const [notificacionModal, setNotificacionModal] = useState<Notificacion | null>(null);

  useEffect(() => {
    void recargar(page, pageSize);
  }, [page, pageSize]);

  const notificacionesFiltradas = filtroTipo === "TODOS"
    ? notificaciones
    : notificaciones.filter((n) => n.tipo === filtroTipo);

  const { ref: listaRef, altoMaximo: altoLista } = useAltoDisponible<HTMLUListElement>(200);

  const marcarTodasLeidas = async () => {
    await notificacionesHttpAdapter.marcarTodasLeidas();
    window.location.reload();
  };

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Notificaciones" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando notificaciones…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  function enlaceModulo(n: Notificacion) {
    if (n.tipo === "STOCK_BAJO") return "/catalogo";
    if (n.tipo === "APERTURA_CAJA" || n.tipo === "CIERRE_CAJA") return "/caja";
    if (n.tipo === "SOLICITUD_INGRESO") return "/aprobaciones";
    return null;
  }

  return (
    <div className="w-full space-y-4">
      <PageHeader
        titulo="Notificaciones"
        descripcion="Avisos del sistema: stock bajo, apertura y cierre de caja y más."
        acciones={
          notificaciones.some((n) => !n.leida) ? (
            <Button
              variante="secundario"
              icono={<CheckCheck className="h-4 w-4" aria-hidden />}
              onClick={() => void marcarTodasLeidas()}
            >
              Marcar todas leídas
            </Button>
          ) : undefined
        }
      />

      <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-row sm:items-end sm:gap-4">
        <div className="sm:flex-1">
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

        {esAdmin && (
          <div className="sm:shrink-0">
            <span className="mb-1 block text-sm font-medium text-zinc-700">Ajustes</span>
            <Button
              variante="secundario"
              className="w-full sm:w-auto"
              icono={<Settings className="h-4 w-4" aria-hidden />}
              onClick={() => setMostrarConfig(true)}
            >
              Configuración
            </Button>
          </div>
        )}
      </div>

      {notificacionesFiltradas.length === 0 ? (
        <Card sinPadding>
          <EmptyState icono={BellOff} titulo="Sin notificaciones" descripcion="Todo tranquilo por ahora." />
        </Card>
      ) : (
        // A diferencia del resto de los listados, este no es una <Table>: sin
        // límite propio estiraba la página y aparecía la barra vertical de la
        // pantalla además de la del listado.
        <ul
          ref={listaRef}
          style={{ maxHeight: altoLista }}
          className="space-y-2.5 overflow-y-auto px-0.5 py-0.5 [scrollbar-gutter:stable]"
        >
          {notificacionesFiltradas.map((n) => (
            <li key={n.id}>
              <div
                onClick={() => setNotificacionModal(n)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setNotificacionModal(n);
                  }
                }}
                className="group cursor-pointer transition-all focus:outline-none"
              >
                <Card className={`transition-all group-hover:border-zinc-300 group-hover:shadow-md ${n.leida ? "opacity-60" : ""}`}>
                  <div className="flex items-start gap-3">
                    <div className={`rounded-full p-2 ${n.leida ? "bg-zinc-100" : "bg-info-suave"}`}>
                      <Bell className={`h-4 w-4 ${n.leida ? "text-zinc-400" : "text-info"}`} aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-zinc-900 group-hover:text-black">{n.titulo}</p>
                        <Badge tono={TONO_TIPO[n.tipo] ?? "neutro"}>{n.tipo.replace("_", " ")}</Badge>
                      </div>
                      <p className="mt-0.5 text-sm text-zinc-600 line-clamp-2">{n.mensaje}</p>
                      <p className="mt-1 text-xs text-zinc-400">
                        {n.created_at ? new Date(n.created_at).toLocaleString("es-PE") : ""}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Card sinPadding className="relative z-30 mt-3">
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

      <Modal
        abierto={notificacionModal !== null}
        titulo={notificacionModal?.titulo ?? "Detalle de notificación"}
        alCerrar={() => setNotificacionModal(null)}
        pie={
          <div className="flex flex-wrap items-center justify-between w-full gap-2">
            <div className="flex gap-2">
              {notificacionModal && (
                <Button
                  variante="secundario"
                  compacto
                  onClick={() => {
                    void marcarLeida(notificacionModal.id);
                    setNotificacionModal({ ...notificacionModal, leida: true });
                  }}
                >
                  {notificacionModal.leida ? "Leída" : "Marcar como leída"}
                </Button>
              )}
              {notificacionModal && enlaceModulo(notificacionModal) && (
                <Link to={enlaceModulo(notificacionModal)!}>
                  <Button variante="secundario" compacto icono={<ExternalLink className="h-3.5 w-3.5" aria-hidden />}>
                    Ir al módulo
                  </Button>
                </Link>
              )}
            </div>
            <Button variante="secundario" compacto onClick={() => setNotificacionModal(null)}>
              Cerrar
            </Button>
          </div>
        }
      >
        {notificacionModal && (
          <div className="space-y-3 py-1">
            <div className="flex items-center gap-2">
              <Badge tono={TONO_TIPO[notificacionModal.tipo] ?? "neutro"}>
                {notificacionModal.tipo.replace("_", " ")}
              </Badge>
              <span className="text-xs text-zinc-400">
                {notificacionModal.created_at
                  ? new Date(notificacionModal.created_at).toLocaleString("es-PE")
                  : ""}
              </span>
            </div>
            <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap">
              {notificacionModal.mensaje}
            </p>
          </div>
        )}
      </Modal>

      <Modal
        abierto={mostrarConfig}
        titulo="Configuración de notificaciones"
        alCerrar={() => setMostrarConfig(false)}
        pie={
          <Button variante="secundario" onClick={() => setMostrarConfig(false)}>
            Cerrar
          </Button>
        }
      >
        {config && (
          <div className="space-y-4 py-2">
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
            <p className="text-xs text-zinc-500">
              La configuración de alertas externas (Telegram y correo electrónico) se administra centralizadamente en el servidor del sistema.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
