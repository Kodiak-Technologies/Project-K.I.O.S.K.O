import { useEffect, useState } from "react";
import { Database, Download, ExternalLink } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
  PaginacionControles,
} from "../../../shared/components/ui";
import { useRespaldos } from "../hooks/useRespaldos";
import { httpClient } from "../../../shared/lib/http-client";
import type { EstadoRespaldo, Respaldo } from "../types";
import { useAuthContext } from "../../../shared/lib/auth-context";

interface DriveStatus {
  autorizado: boolean;
  conectado: boolean;
  expirado: boolean;
  tiene_refresh_token: boolean;
  puede_reconectar: boolean;
  token_expiry: string | null;
  mensaje: string | null;
}

const TONO_ESTADO: Record<EstadoRespaldo, "exito" | "alerta" | "info"> = {
  COMPLETADO: "exito",
  FALLIDO: "alerta",
  PENDIENTE: "info",
};

function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Respaldos() {
  const { usuario } = useAuthContext();
  const isAdmin = usuario?.rol === "ADMIN";
  const { respaldos, paginados, cargando, error, noDisponible, recargar, descargar } =
    useRespaldos();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [driveStatus, setDriveStatus] = useState<DriveStatus | null>(null);
  const [loadingDrive, setLoadingDrive] = useState(false);

  useEffect(() => {
    void recargar(page, pageSize);
  }, [page, pageSize]);

  const fetchDriveStatus = async () => {
    if (!isAdmin) return;
    try {
      setLoadingDrive(true);
      const { data } = await httpClient.get<DriveStatus>("/drive/status");
      setDriveStatus(data);
    } catch (error) {
      console.error("Error al obtener estado de Google Drive:", error);
    } finally {
      setLoadingDrive(false);
    }
  };

  const handleConectarDrive = async () => {
    try {
      const { data } = await httpClient.get<{ auth_url: string }>("/drive/auth-url");
      window.open(data.auth_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      console.error("Error al obtener URL de autorización de Google Drive:", error);
    }
  };

  useEffect(() => {
    fetchDriveStatus();
    const interval = setInterval(fetchDriveStatus, 30000);
    return () => clearInterval(interval);
  }, [isAdmin]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("drive") === "ok" || params.get("drive") === "error") {
      setTimeout(fetchDriveStatus, 500);
    }
  }, [isAdmin]);

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Respaldos" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Respaldo>[] = [
    {
      titulo: "Archivo",
      ancho: "230px",
      render: (r) => <span className="font-mono text-xs text-zinc-700">{r.archivo_nombre}</span>,
    },
    {
      titulo: "Tamaño",
      ancho: "90px",
      alinear: "derecha",
      render: (r) => <span className="tabular-nums">{formatearTamano(r.tamano_bytes)}</span>,
    },
    {
      titulo: "Estado",
      ancho: "125px",
      alinear: "centro",
      render: (r) => <Badge tono={TONO_ESTADO[r.estado]}>{r.estado}</Badge>,
    },
    {
      titulo: "Generado",
      ancho: "175px",
      alinear: "centro",
      render: (r) => (
        <span className="whitespace-nowrap text-zinc-500">
          {r.generado_en ? new Date(r.generado_en).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Expira",
      ancho: "100px",
      alinear: "centro",
      render: (r) => (
        <span className="whitespace-nowrap text-zinc-500">
          {r.expira_en ? new Date(r.expira_en).toLocaleDateString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Creado por",
      ancho: "130px",
      alinear: "centro",
      render: (r) => (
        <span className="text-zinc-600">{r.usuario_nombre ?? "—"}</span>
      ),
    },
    {
      titulo: "Acción",
      ancho: "90px",
      alinear: "centro",
      render: (r) =>
        r.estado === "COMPLETADO" ? (
          <div className="flex justify-center">
            <Button
              variante="fantasma"
              compacto
              title="Descargar respaldo"
              aria-label="Descargar respaldo"
              onClick={() => void descargar(r.id, r.archivo_nombre)}
              icono={<Download className="h-4 w-4 text-zinc-600" aria-hidden />}
            />
          </div>
        ) : (
          <span className="text-xs text-zinc-400">—</span>
        ),
    },
  ];

  return (
    <div>
      <PageHeader titulo="Respaldos" descripcion="Copias de seguridad de la base de datos." />

      {driveStatus !== null && !driveStatus.conectado && (
        <div className="mb-4">
          <Alert tono="alerta">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between w-full">
              <span>Google Drive no está conectado.</span>
              <Button
                onClick={handleConectarDrive}
                disabled={loadingDrive}
                className="w-full sm:w-auto"
                compacto
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                Conectar a Google Drive
              </Button>
            </div>
          </Alert>
        </div>
      )}

      {cargando && <PageSpinner texto="Cargando respaldos…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            minAncho="940px"
            columnas={columnas}
            filas={respaldos}
            claveDe={(r) => r.id}
            vacio={
              <EmptyState
                icono={Database}
                titulo="Sin respaldos"
                descripcion="Aún no se ha generado ningún respaldo."
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={(n) => {
              setPageSize(n);
              setPage(1);
            }}
            etiqueta="respaldos"
          />
        </Card>
      )}
    </div>
  );
}
