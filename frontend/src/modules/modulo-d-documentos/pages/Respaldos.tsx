import { Database, Download, Plus, RotateCcw } from "lucide-react";
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
} from "../../../shared/components/ui";
import { useRespaldos } from "../hooks/useRespaldos";
import type { EstadoRespaldo, Respaldo } from "../types";

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
  const { respaldos, cargando, error, noDisponible, crear, descargar, restaurar } = useRespaldos();

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Respaldos" />
        <Card sinPadding>
          <ModuloPendiente modulo="documentos (Módulo D)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Respaldo>[] = [
    {
      titulo: "Archivo",
      render: (r) => <span className="font-mono text-xs text-zinc-700">{r.archivo_nombre}</span>,
    },
    {
      titulo: "Tamaño",
      alinear: "derecha",
      render: (r) => <span className="tabular-nums">{formatearTamano(r.tamano_bytes)}</span>,
    },
    {
      titulo: "Estado",
      render: (r) => <Badge tono={TONO_ESTADO[r.estado]}>{r.estado}</Badge>,
    },
    {
      titulo: "Generado",
      render: (r) => (
        <span className="whitespace-nowrap text-zinc-500">
          {r.generado_en ? new Date(r.generado_en).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Expira",
      render: (r) => (
        <span className="whitespace-nowrap text-zinc-500">
          {r.expira_en ? new Date(r.expira_en).toLocaleDateString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Acción",
      render: (r) =>
        r.estado === "COMPLETADO" ? (
          <div className="flex gap-1">
            <Button
              variante="secundario"
              compacto
              icono={<Download className="h-4 w-4" aria-hidden />}
              onClick={() => void descargar(r.id, r.archivo_nombre)}
            >
              Descargar
            </Button>
            <Button
              variante="secundario"
              compacto
              icono={<RotateCcw className="h-4 w-4" aria-hidden />}
              onClick={() => void restaurar(r.id)}
            >
              Restaurar
            </Button>
          </div>
        ) : (
          <span className="text-xs text-zinc-400">—</span>
        ),
    },
  ];

  return (
    <div>
      <PageHeader titulo="Respaldos" descripcion="Copias de seguridad de la base de datos." />

      <Card className="mb-4">
        <Button onClick={() => void crear()} icono={<Plus className="h-4 w-4" aria-hidden />}>
          Crear respaldo
        </Button>
      </Card>

      {cargando && <PageSpinner texto="Cargando respaldos…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
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
        </Card>
      )}
    </div>
  );
}
