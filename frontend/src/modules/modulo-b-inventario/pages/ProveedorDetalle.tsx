// Detalle de un proveedor: datos, deuda actual, historial de pagos/compras a crédito.
// Solo ADMIN. Permite registrar compras a crédito y pagos.
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
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
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { FormularioPago } from "../components/FormularioPago";
import { PaginacionControles } from "../components/PaginacionControles";
import { useProveedores } from "../hooks/useProveedores";
import type { FiltrosPagosProveedor, PagoProveedor, Proveedor, TipoPago } from "../types";
import { ScrollText } from "lucide-react";

const TONO_TIPO_PAGO: Record<string, Tono> = {
  compra_credito: "alerta",
  pago: "exito",
  COMPRA_CREDITO: "alerta",
  PAGO: "exito",
};

const TIPO_LABELS: Record<string, string> = {
  compra_credito: "Compra a crédito",
  pago: "Pago",
};

export default function ProveedorDetalle() {
  const { id } = useParams<{ id: string }>();
  const proveedorId = id ? Number(id) : null;
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";

  const { obtener, listarPagos, registrarCompraCredito, registrarPago } = useProveedores();

  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  const [deudaActual, setDeudaActual] = useState<number>(0);
  const [pagos, setPagos] = useState<PagoProveedor[]>([]);
  const [paginados, setPaginados] = useState<{ total: number; total_pages: number } | null>(null);
  const [filtroTipo, setFiltroTipo] = useState<TipoPago | "">("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const [modalCompra, setModalCompra] = useState(false);
  const [modalPago, setModalPago] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    if (!proveedorId) return;
    try {
      const prov = await obtener(proveedorId);
      setProveedor(prov);
      setDeudaActual(prov.deuda_actual);
      const filtros: FiltrosPagosProveedor = { page, page_size: pageSize };
      if (filtroTipo) filtros.tipo = filtroTipo;
      const respPagos = await listarPagos(proveedorId, filtros);
      setPagos(respPagos.items);
      setDeudaActual(respPagos.deuda_actual);
      setPaginados({ total: respPagos.total, total_pages: respPagos.total_pages });
    } catch (e) {
      if (e instanceof Error && /404|501|503/.test(e.message)) setNoDisponible(true);
      setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, [proveedorId, page, pageSize, filtroTipo, obtener, listarPagos]);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  async function manejarCompraCredito(datos: Parameters<typeof registrarCompraCredito>[1]) {
    if (!proveedorId) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await registrarCompraCredito(proveedorId, datos);
      setMensaje("Compra a crédito registrada.");
      setModalCompra(false);
      await recargar();
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
      throw e;
    } finally {
      setProcesando(false);
    }
  }

  async function manejarPago(datos: Parameters<typeof registrarPago>[1]) {
    if (!proveedorId) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await registrarPago(proveedorId, datos);
      setMensaje("Pago registrado.");
      setModalPago(false);
      await recargar();
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
      throw e;
    } finally {
      setProcesando(false);
    }
  }

  if (!esAdmin) {
    return (
      <div>
        <PageHeader titulo="Detalle de proveedor" />
        <Card sinPadding>
          <Alert tono="peligro">Esta sección es solo para ADMIN.</Alert>
        </Card>
      </div>
    );
  }
  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Detalle de proveedor" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando proveedor…" />;
  if (error || !proveedor) return <Alert tono="peligro">{error ?? "Proveedor no encontrado."}</Alert>;

  const columnas: Columna<PagoProveedor>[] = [
    {
      titulo: "Fecha",
      render: (p) => (
        <span className="whitespace-nowrap text-zinc-500">
          {p.fecha ? new Date(p.fecha).toLocaleDateString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Tipo",
      render: (p) => {
        const t = String(p.tipo);
        return <Badge tono={TONO_TIPO_PAGO[t] ?? "neutro"}>{TIPO_LABELS[t] ?? t}</Badge>;
      },
    },
    {
      titulo: "Monto",
      alinear: "derecha",
      render: (p) => (
        <span className={`tabular-nums ${p.tipo === "pago" ? "text-green-700" : "text-peligro"}`}>
          {p.tipo === "pago" ? "−" : "+"} S/ {p.monto.toFixed(2)}
        </span>
      ),
    },
    {
      titulo: "Concepto",
      soloEscritorio: true,
      render: (p) =>
        p.concepto ? <span className="line-clamp-1 max-w-xs">{p.concepto}</span> : "—",
    },
    {
      titulo: "Solicitud",
      soloEscritorio: true,
      render: (p) => (p.solicitud_ingreso_id ? `#${p.solicitud_ingreso_id}` : "—"),
    },
    { titulo: "Registró", soloEscritorio: true, render: (p) => p.registrado_por_nombre },
    {
      titulo: "Deuda tras op.",
      alinear: "derecha",
      soloEscritorio: true,
      render: (p) => <span className="tabular-nums text-zinc-500">S/ {p.deuda_actual.toFixed(2)}</span>,
    },
  ];

  return (
    <div>
      <PageHeader
        titulo={proveedor.razon_social}
        descripcion={`Detalle del proveedor · ${proveedor.ruc ?? "sin RUC"}`}
        acciones={
          <Link to="/proveedores" className="text-sm text-marca-secundario hover:underline">
            ← Volver al listado
          </Link>
        }
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}

      <div className="mb-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card titulo="Datos">
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-zinc-500">Razón social</dt>
              <dd className="font-medium">{proveedor.razon_social}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">RUC</dt>
              <dd>{proveedor.ruc ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Teléfono</dt>
              <dd>{proveedor.telefono ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Email</dt>
              <dd className="break-all">{proveedor.email ?? "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-zinc-500">Dirección</dt>
              <dd>{proveedor.direccion ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Estado</dt>
              <dd>
                <Badge tono={proveedor.activo ? "exito" : "neutro"}>
                  {proveedor.activo ? "Activo" : "Inactivo"}
                </Badge>
              </dd>
            </div>
          </dl>
        </Card>
        <Card titulo="Deuda actual">
          <div className="space-y-3">
            <p
              className={`text-3xl font-bold tabular-nums ${
                deudaActual > 0 ? "text-peligro" : "text-green-700"
              }`}
            >
              S/ {deudaActual.toFixed(2)}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => { setModalCompra(true); setErrorAccion(null); }}>
                Registrar compra a crédito
              </Button>
              <Button
                variante="secundario"
                disabled={deudaActual <= 0}
                onClick={() => { setModalPago(true); setErrorAccion(null); }}
              >
                Registrar pago
              </Button>
            </div>
            {deudaActual <= 0 && (
              <p className="text-xs text-zinc-500">No hay deuda pendiente para pagar.</p>
            )}
          </div>
        </Card>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-zinc-700">Tipo de movimiento</span>
          <select
            value={filtroTipo}
            onChange={(e) => {
              setFiltroTipo(e.target.value as TipoPago | "");
              setPage(1);
            }}
            className="min-h-tactil rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">Todos</option>
            <option value="compra_credito">Compras a crédito</option>
            <option value="pago">Pagos</option>
          </select>
        </label>
      </div>

      <Card sinPadding>
        <Table
          columnas={columnas}
          filas={pagos}
          claveDe={(p) => p.id}
          vacio={
            <EmptyState
              icono={ScrollText}
              titulo="Sin movimientos"
              descripcion="Cuando registres una compra o un pago, aparecerá acá."
            />
          }
        />
        {paginados && (
          <PaginacionControles
            paginados={{ total: paginados.total, total_pages: paginados.total_pages }}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={setPageSize}
            etiqueta="movimientos"
          />
        )}
      </Card>

      {/* Modal: compra a crédito */}
      <Modal
        abierto={modalCompra}
        titulo="Registrar compra a crédito"
        alCerrar={() => !procesando && setModalCompra(false)}
      >
        {errorAccion && <div className="mb-3"><Alert tono="peligro">{errorAccion}</Alert></div>}
        <FormularioPago
          titulo={`Suma a la deuda actual (S/ ${deudaActual.toFixed(2)}).`}
          tipo="COMPRA_CREDITO"
          deudaActual={deudaActual}
          onSubmit={manejarCompraCredito}
          procesando={procesando}
          onCancelar={() => setModalCompra(false)}
        />
      </Modal>

      {/* Modal: pago */}
      <Modal
        abierto={modalPago}
        titulo="Registrar pago"
        alCerrar={() => !procesando && setModalPago(false)}
      >
        {errorAccion && <div className="mb-3"><Alert tono="peligro">{errorAccion}</Alert></div>}
        <FormularioPago
          titulo={`Descuenta de la deuda actual (S/ ${deudaActual.toFixed(2)}).`}
          tipo="PAGO"
          deudaActual={deudaActual}
          onSubmit={manejarPago}
          procesando={procesando}
          onCancelar={() => setModalPago(false)}
        />
      </Modal>
    </div>
  );
}
