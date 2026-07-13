// Página de historial de ventas con filtros. Anular requiere permiso de ADMIN
// (el backend lo valida); acá solo se muestra la acción al ADMIN.
import { useState } from "react";
import { History } from "lucide-react";
import {
  Alert,
  Badge,
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
import { useAuthContext } from "../../../shared/lib/auth-context";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useVenta } from "../hooks/useVenta";
import type { Venta } from "../types";

export default function HistorialVentas() {
  const { usuario } = useAuthContext();
  const { ventas, cargando, error, noDisponible, recargar, anular } = useVenta();
  const esAdmin = usuario?.rol === "ADMIN";

  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [paraAnular, setParaAnular] = useState<Venta | null>(null);
  const [motivo, setMotivo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  async function manejarAnular() {
    if (!paraAnular) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await anular(paraAnular.id, motivo);
      setMensaje(`Venta #${paraAnular.id} anulada. Quedó registrada en la bitácora.`);
      setParaAnular(null);
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
        <PageHeader titulo="Historial de ventas" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas (Módulo C)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Venta>[] = [
    { titulo: "N°", render: (v) => <span className="font-mono text-xs text-zinc-500">#{v.id}</span> },
    {
      titulo: "Fecha",
      render: (v) => (
        <span className="whitespace-nowrap text-zinc-500">
          {v.created_at ? new Date(v.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Items",
      soloEscritorio: true,
      render: (v) => (
        <span className="text-zinc-600">
          {v.items.map((i) => `${i.cantidad}× ${i.nombre}`).join(", ")}
        </span>
      ),
    },
    { titulo: "Vendedor", soloEscritorio: true, render: (v) => v.vendedor },
    { titulo: "Pago", render: (v) => <Badge tono="neutro">{v.metodo_pago}</Badge> },
    {
      titulo: "Total",
      alinear: "derecha",
      render: (v) => (
        <span className={`font-medium tabular-nums ${v.anulada ? "text-zinc-400 line-through" : "text-zinc-900"}`}>
          S/ {v.total.toFixed(2)}
        </span>
      ),
    },
    {
      titulo: "Estado",
      render: (v) =>
        v.anulada ? <Badge tono="peligro">Anulada</Badge> : <Badge tono="exito">Válida</Badge>,
    },
    ...(esAdmin
      ? [
          {
            titulo: "Acciones",
            render: (v: Venta) =>
              v.anulada ? null : (
                <Button variante="secundario" compacto className="text-peligro" onClick={() => setParaAnular(v)}>
                  Anular
                </Button>
              ),
          } satisfies Columna<Venta>,
        ]
      : []),
  ];

  return (
    <div>
      <PageHeader titulo="Historial de ventas" descripcion="Todas las ventas registradas en el POS." />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-44">
            <Input label="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          </div>
          <div className="w-44">
            <Input label="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          </div>
          <Button
            variante="secundario"
            onClick={() => void recargar(desde || undefined, hasta || undefined)}
          >
            Filtrar
          </Button>
        </div>
      </Card>

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}
      {cargando && <PageSpinner texto="Cargando ventas…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={ventas}
            claveDe={(v) => v.id}
            vacio={
              <EmptyState
                icono={History}
                titulo="Sin ventas"
                descripcion="Aún no hay ventas en el período elegido."
              />
            }
          />
        </Card>
      )}

      <Modal
        abierto={paraAnular !== null}
        titulo={`Anular venta #${paraAnular?.id}`}
        alCerrar={() => setParaAnular(null)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setParaAnular(null)}>
              Cancelar
            </Button>
            <Button variante="peligro" cargando={procesando} onClick={() => void manejarAnular()}>
              Anular venta
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-zinc-600">
            La anulación devuelve el stock y queda registrada en la bitácora con tu usuario.
          </p>
          <Input
            label="Motivo"
            requerido
            placeholder="ej. cobro duplicado"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
        </div>
      </Modal>
    </div>
  );
}
