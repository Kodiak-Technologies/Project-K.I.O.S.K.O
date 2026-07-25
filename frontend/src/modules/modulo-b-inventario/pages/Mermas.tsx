// Página de mermas: CAJERO y ADMIN pueden registrar (paso 1). ADMIN ve la cola
// de "Registrada" y puede confirmar/rechazar.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PackageX } from "lucide-react";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { FormularioMerma } from "../components/FormularioMerma";
import { PaginacionControles } from "../components/PaginacionControles";
import { useMermas } from "../hooks/useMermas";
import { useProductos } from "../hooks/useProductos";
import type { EstadoMerma, FiltrosMermas, Merma, MotivoMerma } from "../types";

const TONO_ESTADO: Record<string, Tono> = {
  Registrada: "alerta",
  Confirmada: "exito",
  Rechazada: "peligro",
};

const MOTIVO_LABELS: Record<string, string> = {
  vencimiento: "Vencimiento",
  rotura: "Rotura",
  otro: "Otro",
};

export default function Mermas() {
  const [searchParams, setSearchParams] = useSearchParams();
  const productoInicial = searchParams.get("producto_id");
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";

  const { mermas, paginados, cargando, error, noDisponible, recargar, registrar, confirmar, rechazar } =
    useMermas();
  const { productos } = useProductos({ page_size: 200 });

  const [filtroEstado, setFiltroEstado] = useState<EstadoMerma | "">("Registrada");
  const [filtroMotivo, setFiltroMotivo] = useState<MotivoMerma | "">("");
  const [filtroProducto, setFiltroProducto] = useState<number | "">("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [procesandoAccion, setProcesandoAccion] = useState<number | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  useEffect(() => {
    const filtros: FiltrosMermas = { page, page_size: pageSize };
    if (filtroEstado) filtros.estado = filtroEstado;
    if (filtroMotivo) filtros.motivo = filtroMotivo;
    if (filtroProducto) filtros.producto_id = filtroProducto;
    void recargar(filtros);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroEstado, filtroMotivo, filtroProducto, page, pageSize]);

  // Si la URL trae ?producto_id=NNN, pre-cargar el formulario y limpiar la query.
  useEffect(() => {
    if (productoInicial) {
      const next = new URLSearchParams(searchParams);
      next.delete("producto_id");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productoInicial]);

  function nombreProducto(id: number): string {
    return productos.find((p) => p.id === id)?.nombre ?? `#${id}`;
  }

  async function manejarRegistrar(datos: Parameters<typeof registrar>[0]) {
    setErrorAccion(null);
    try {
      await registrar(datos);
      setMensaje("Merma registrada. Queda pendiente de confirmación del ADMIN.");
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : "No se pudo registrar.");
      throw e;
    }
  }

  async function manejarConfirmar(m: Merma) {
    setProcesandoAccion(m.id);
    setErrorAccion(null);
    try {
      await confirmar(m.id);
      setMensaje(`Merma #${m.id} confirmada: stock actualizado.`);
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : "No se pudo confirmar.");
    } finally {
      setProcesandoAccion(null);
    }
  }

  async function manejarRechazar(m: Merma) {
    const motivo = window.prompt("Motivo del rechazo (mínimo 5 caracteres):", "");
    if (!motivo || motivo.trim().length < 5) {
      if (motivo !== null) setErrorAccion("El motivo debe tener al menos 5 caracteres.");
      return;
    }
    setProcesandoAccion(m.id);
    setErrorAccion(null);
    try {
      await rechazar(m.id, { motivo_rechazo: motivo.trim() });
      setMensaje(`Merma #${m.id} rechazada.`);
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : "No se pudo rechazar.");
    } finally {
      setProcesandoAccion(null);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Mermas" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Merma>[] = [
    {
      titulo: "Fecha",
      render: (m) => (
        <span className="whitespace-nowrap text-zinc-500">
          {m.created_at ? new Date(m.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    { titulo: "Producto", render: (m) => nombreProducto(m.producto_id) },
    {
      titulo: "Cantidad",
      alinear: "derecha",
      render: (m) => <span className="tabular-nums">{m.cantidad}</span>,
    },
    {
      titulo: "Motivo",
      soloEscritorio: true,
      render: (m) => MOTIVO_LABELS[String(m.motivo)] ?? m.motivo,
    },
    {
      titulo: "Observación",
      soloEscritorio: true,
      render: (m) =>
        m.observacion ? (
          <span className="line-clamp-2 max-w-xs text-xs text-zinc-600">{m.observacion}</span>
        ) : (
          "—"
        ),
    },
    {
      titulo: "Estado",
      render: (m) => {
        const estado = String(m.estado);
        return (
          <div>
            <Badge tono={TONO_ESTADO[estado] ?? "neutro"}>{estado}</Badge>
            {m.motivo_rechazo && <p className="mt-1 text-xs text-zinc-500">{m.motivo_rechazo}</p>}
          </div>
        );
      },
    },
    ...(esAdmin
      ? [
          {
            titulo: "Acciones",
            render: (m: Merma) => {
              if (String(m.estado) !== "Registrada") return null;
              return (
                <div className="flex gap-1">
                  <ButtonCompact
                    cargando={procesandoAccion === m.id}
                    onClick={() => void manejarConfirmar(m)}
                    variante="primario"
                  >
                    Confirmar
                  </ButtonCompact>
                  <ButtonCompact
                    cargando={procesandoAccion === m.id}
                    onClick={() => void manejarRechazar(m)}
                    variante="peligro"
                  >
                    Rechazar
                  </ButtonCompact>
                </div>
              );
            },
          } as Columna<Merma>,
        ]
      : []),
  ];

  return (
    <div>
      <PageHeader
        titulo="Mermas"
        descripcion="Reportá pérdidas o vencimientos. El ADMIN las confirma para que descuenten del stock."
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

      <div className="mb-4">
        <FormularioMerma
          alRegistrar={manejarRegistrar}
          procesando={false}
          productoInicialId={productoInicial ? Number(productoInicial) : null}
        />
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <Select
          label="Estado"
          value={filtroEstado}
          onChange={(e) => {
            setFiltroEstado(e.target.value as EstadoMerma | "");
            setPage(1);
          }}
          className="max-w-xs"
        >
          {esAdmin && <option value="Registrada">Pendientes (Registrada)</option>}
          <option value="Confirmada">Confirmadas</option>
          <option value="Rechazada">Rechazadas</option>
          {!esAdmin && <option value="">Todas las mías</option>}
        </Select>
        <Select
          label="Motivo"
          value={filtroMotivo}
          onChange={(e) => {
            setFiltroMotivo(e.target.value as MotivoMerma | "");
            setPage(1);
          }}
          className="max-w-xs"
        >
          <option value="">Todos</option>
          <option value="vencimiento">Vencimiento</option>
          <option value="rotura">Rotura</option>
          <option value="otro">Otro</option>
        </Select>
        <Select
          label="Producto"
          value={filtroProducto}
          onChange={(e) => {
            setFiltroProducto(e.target.value ? Number(e.target.value) : "");
            setPage(1);
          }}
          className="max-w-xs"
        >
          <option value="">Todos</option>
          {productos.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nombre}
            </option>
          ))}
        </Select>
      </div>

      {cargando && mermas.length === 0 ? (
        <PageSpinner texto="Cargando mermas…" />
      ) : error ? (
        <Alert tono="peligro">{error}</Alert>
      ) : (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={mermas}
            claveDe={(m) => m.id}
            vacio={
              <EmptyState
                icono={PackageX}
                titulo="Sin mermas"
                descripcion={
                  filtroEstado
                    ? `No hay mermas con estado ${filtroEstado}.`
                    : "Cuando registres una merma, aparecerá acá."
                }
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={setPageSize}
            etiqueta="mermas"
          />
        </Card>
      )}
    </div>
  );
}

// Mini-botonera local (evita acoplar el Button del sistema con un `disabled` raro).
import { Button } from "../../../shared/components/ui";
function ButtonCompact({
  children,
  onClick,
  cargando,
  variante = "secundario",
}: {
  children: React.ReactNode;
  onClick: () => void;
  cargando?: boolean;
  variante?: "primario" | "secundario" | "peligro";
}) {
  return (
    <Button compacto onClick={onClick} cargando={cargando} variante={variante}>
      {children}
    </Button>
  );
}
