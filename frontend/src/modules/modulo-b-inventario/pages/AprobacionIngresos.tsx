// Página para aprobar o rechazar ingresos de mercadería pendientes (solo ADMIN).
import { useState } from "react";
import { Check, ClipboardCheck, X } from "lucide-react";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useIngresos } from "../hooks/useIngresos";
import type { IngresoMercaderia } from "../types";

export default function AprobacionIngresos() {
  const { ingresos, cargando, error, noDisponible, aprobar, rechazar } = useIngresos();

  const [paraRechazar, setParaRechazar] = useState<IngresoMercaderia | null>(null);
  const [motivo, setMotivo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const pendientes = ingresos.filter((i) => i.estado === "PENDIENTE");

  async function manejarAprobar(ingreso: IngresoMercaderia) {
    setErrorAccion(null);
    setMensaje(null);
    try {
      await aprobar(ingreso.id);
      setMensaje(`Ingreso de '${ingreso.producto}' aprobado: el stock ya se actualizó.`);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
  }

  async function manejarRechazar() {
    if (!paraRechazar) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await rechazar(paraRechazar.id, motivo);
      setMensaje(`Ingreso de '${paraRechazar.producto}' rechazado.`);
      setParaRechazar(null);
      setMotivo("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Aprobación de ingresos" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando pendientes…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const columnas: Columna<IngresoMercaderia>[] = [
    {
      titulo: "Fecha",
      render: (i) => (
        <span className="whitespace-nowrap text-zinc-500">
          {i.created_at ? new Date(i.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    { titulo: "Producto", render: (i) => <span className="font-medium text-zinc-800">{i.producto}</span> },
    { titulo: "Cantidad", alinear: "derecha", render: (i) => <span className="tabular-nums">{i.cantidad}</span> },
    { titulo: "Solicitado por", render: (i) => i.solicitado_por },
    {
      titulo: "Acciones",
      render: (i) => (
        <div className="flex gap-2">
          <Button
            compacto
            onClick={() => void manejarAprobar(i)}
            icono={<Check className="h-4 w-4" aria-hidden />}
          >
            Aprobar
          </Button>
          <Button
            variante="secundario"
            compacto
            className="text-peligro"
            onClick={() => setParaRechazar(i)}
            icono={<X className="h-4 w-4" aria-hidden />}
          >
            Rechazar
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Aprobación de ingresos"
        descripcion="Solo lo aprobado suma al stock. Cada decisión queda en la bitácora."
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}
      {errorAccion && (
        <div className="mb-4">
          <Alert tono="peligro">{errorAccion}</Alert>
        </div>
      )}

      <Card sinPadding>
        <Table
          columnas={columnas}
          filas={pendientes}
          claveDe={(i) => i.id}
          vacio={
            <EmptyState
              icono={ClipboardCheck}
              titulo="Nada pendiente"
              descripcion="No hay ingresos esperando aprobación."
            />
          }
        />
      </Card>

      <Modal
        abierto={paraRechazar !== null}
        titulo={`Rechazar ingreso de '${paraRechazar?.producto}'`}
        alCerrar={() => setParaRechazar(null)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setParaRechazar(null)}>
              Cancelar
            </Button>
            <Button variante="peligro" cargando={procesando} onClick={() => void manejarRechazar()}>
              Rechazar ingreso
            </Button>
          </>
        }
      >
        <Input
          label="Motivo del rechazo"
          requerido
          placeholder="ej. cantidad no coincide con la guía"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
      </Modal>
    </div>
  );
}
