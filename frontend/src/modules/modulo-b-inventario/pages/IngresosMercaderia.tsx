// Página para registrar nuevos ingresos de mercadería. El CAJERO solicita;
// el ADMIN los aprueba en la página de Aprobaciones.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, Truck } from "lucide-react";
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
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { FormularioLineaIngreso, type LineaIngreso } from "../components/FormularioLineaIngreso";
import { PaginacionControles } from "../components/PaginacionControles";
import { SubirImagen } from "../components/SubirImagen";
import { useIngresos } from "../hooks/useIngresos";
import { useProductos } from "../hooks/useProductos";
import { useProveedores } from "../hooks/useProveedores";
import type { EstadoIngreso, FiltrosIngresos, SolicitudIngreso } from "../types";

const TONO_ESTADO: Record<string, Tono> = {
  Pendiente: "alerta",
  Aprobada: "exito",
  Rechazada: "peligro",
};

const LINEA_VACIA: LineaIngreso = { producto_id: null, cantidad: 1, precio_compra_unitario: 0 };

export default function IngresosMercaderia() {
  const [searchParams, setSearchParams] = useSearchParams();
  const productoInicial = searchParams.get("producto_id");

  const { ingresos, paginados, cargando, error, noDisponible, recargar, solicitar } = useIngresos();
  const { productos } = useProductos({ page_size: 200 });
  const { proveedores } = useProveedores({ page_size: 100 });

  const [lineas, setLineas] = useState<LineaIngreso[]>([LINEA_VACIA]);
  const [proveedorId, setProveedorId] = useState<number | "">("");
  const [fotoUrl, setFotoUrl] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState<EstadoIngreso | "">("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Si la URL trae ?producto_id=NNN, pre-cargamos la primera línea.
  useEffect(() => {
    if (productoInicial) {
      setLineas([{ ...LINEA_VACIA, producto_id: Number(productoInicial) }]);
      // Limpiamos la query para no re-disparar al recargar la lista.
      const next = new URLSearchParams(searchParams);
      next.delete("producto_id");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productoInicial]);

  // Re-cargar lista cuando cambia filtro o paginación.
  useEffect(() => {
    const filtros: FiltrosIngresos = { page, page_size: pageSize };
    if (filtroEstado) filtros.estado = filtroEstado;
    void recargar(filtros);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroEstado, page, pageSize]);

  function agregarLinea() {
    setLineas([...lineas, LINEA_VACIA]);
  }
  function eliminarLinea(idx: number) {
    setLineas(lineas.filter((_, i) => i !== idx));
  }
  function actualizarLinea(idx: number, l: LineaIngreso) {
    setLineas(lineas.map((actual, i) => (i === idx ? l : actual)));
  }

  function validar(): string | null {
    if (!fotoUrl) return "Subí la foto de la boleta (obligatoria).";
    if (lineas.length === 0) return "Agregá al menos una línea.";
    for (let i = 0; i < lineas.length; i++) {
      const l = lineas[i];
      if (!l.producto_id) return `Línea ${i + 1}: elegí un producto.`;
      if (l.cantidad < 1) return `Línea ${i + 1}: la cantidad debe ser mayor a 0.`;
      if (l.precio_compra_unitario < 0) return `Línea ${i + 1}: el precio no puede ser negativo.`;
    }
    return null;
  }

  async function manejarSolicitar() {
    setErrorAccion(null);
    setMensaje(null);
    const errorValid = validar();
    if (errorValid) {
      setErrorAccion(errorValid);
      return;
    }
    setProcesando(true);
    try {
      // `validar()` ya garantizó que fotoUrl no es null.
      await solicitar({
        foto_boleta_url: fotoUrl!,
        proveedor_id: proveedorId === "" ? null : Number(proveedorId),
        lineas: lineas.map((l) => ({
          producto_id: l.producto_id!,
          cantidad: l.cantidad,
          precio_compra_unitario: l.precio_compra_unitario,
        })),
      });
      setMensaje("Ingreso registrado. Queda pendiente de aprobación del ADMIN.");
      setLineas([LINEA_VACIA]);
      setProveedorId("");
      setFotoUrl(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Ingresos de mercadería" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<SolicitudIngreso>[] = [
    {
      titulo: "Fecha",
      render: (i) => (
        <span className="whitespace-nowrap text-zinc-500">
          {i.created_at ? new Date(i.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Productos",
      render: (i) => (
        <div>
          <span className="font-medium text-zinc-800">
            {i.cantidad_productos ?? i.lineas.length} unidades
          </span>
          <p className="text-xs text-zinc-500">{i.lineas.length} línea(s)</p>
        </div>
      ),
    },
    {
      titulo: "Monto",
      alinear: "derecha",
      soloEscritorio: true,
      render: (i) => (
        <span className="tabular-nums">
          {i.monto_total != null ? `S/ ${i.monto_total.toFixed(2)}` : "—"}
        </span>
      ),
    },
    {
      titulo: "Solicitado por",
      soloEscritorio: true,
      render: (i) => i.solicitado_por_nombre,
    },
    {
      titulo: "Estado",
      render: (i) => {
        const estado = String(i.estado);
        const tono = TONO_ESTADO[estado] ?? "neutro";
        return (
          <div>
            <Badge tono={tono}>{estado}</Badge>
            {i.motivo_rechazo && <p className="mt-1 text-xs text-zinc-500">{i.motivo_rechazo}</p>}
          </div>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Ingresos de mercadería"
        descripcion="Registrá lo que llega a tienda; el ADMIN lo aprueba y recién ahí suma al stock."
      />

      <Card titulo="Registrar ingreso" className="mb-4" descripcion="Subí la foto de la boleta y una o más líneas con productos y costos.">
        <div className="space-y-4">
          <SubirImagen
            carpeta="boletas"
            label="Foto de la boleta"
            ayuda="Obligatoria. JPG/PNG. Se guarda en Storage y queda en la solicitud."
            requerido
            value={fotoUrl}
            onChange={setFotoUrl}
            error={!fotoUrl && errorAccion?.includes("foto") ? errorAccion : null}
          />
          <Select
            label="Proveedor (opcional)"
            value={proveedorId}
            onChange={(e) => setProveedorId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Sin proveedor</option>
            {proveedores.map((p) => (
              <option key={p.id} value={p.id}>
                {p.razon_social}
              </option>
            ))}
          </Select>
          <div className="space-y-3">
            {lineas.map((l, i) => (
              <FormularioLineaIngreso
                key={i}
                linea={l}
                productos={productos}
                esUnica={lineas.length === 1}
                onChange={(nl) => actualizarLinea(i, nl)}
                onEliminar={() => eliminarLinea(i)}
              />
            ))}
            <Button type="button" variante="secundario" onClick={agregarLinea} icono={<Plus className="h-4 w-4" aria-hidden />}>
              Agregar línea
            </Button>
          </div>
          {mensaje && <Alert tono="exito">{mensaje}</Alert>}
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
          <div className="flex justify-end">
            <Button onClick={() => void manejarSolicitar()} cargando={procesando} icono={<Truck className="h-4 w-4" aria-hidden />}>
              Registrar ingreso
            </Button>
          </div>
        </div>
      </Card>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <Select
          label="Filtrar por estado"
          value={filtroEstado}
          onChange={(e) => {
            setFiltroEstado(e.target.value as EstadoIngreso | "");
            setPage(1);
          }}
          className="max-w-xs"
        >
          <option value="">Todos</option>
          <option value="Pendiente">Pendientes</option>
          <option value="Aprobada">Aprobados</option>
          <option value="Rechazada">Rechazados</option>
        </Select>
      </div>

      {cargando && <PageSpinner texto="Cargando ingresos…" />}
      {error && <Alert tono="peligro">{error}</Alert>}

      {!cargando && !error && (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={ingresos}
            claveDe={(i) => i.id}
            vacio={
              <EmptyState
                icono={Truck}
                titulo="Sin ingresos registrados"
                descripcion={
                  filtroEstado
                    ? `No hay ingresos con estado ${filtroEstado}.`
                    : "Cuando llegue mercadería, regístrala aquí."
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
            etiqueta="ingresos"
          />
        </Card>
      )}
    </div>
  );
}
