// Página para registrar nuevos ingresos de mercadería. El CAJERO solicita;
// el ADMIN los aprueba en la página de Aprobaciones.
import { useState, type FormEvent } from "react";
import { Truck } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ModuloPendiente,
  PageHeader,
  PageSpinner,
  Select,
  Table,
  type Columna,
  type Tono,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useIngresos } from "../hooks/useIngresos";
import { useProductos } from "../hooks/useProductos";
import type { EstadoIngreso, IngresoMercaderia } from "../types";

const TONO_ESTADO: Record<EstadoIngreso, Tono> = {
  PENDIENTE: "alerta",
  APROBADO: "exito",
  RECHAZADO: "peligro",
};

export default function IngresosMercaderia() {
  const { ingresos, cargando, error, noDisponible, solicitar } = useIngresos();
  const { productos } = useProductos();

  const [productoId, setProductoId] = useState<number | "">("");
  const [cantidad, setCantidad] = useState(1);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  async function manejarSolicitar(evento: FormEvent) {
    evento.preventDefault();
    setErrorAccion(null);
    setMensaje(null);
    if (productoId === "" || cantidad < 1) {
      setErrorAccion("Elige un producto y una cantidad mayor a 0.");
      return;
    }
    setProcesando(true);
    try {
      // TODO PR3b: el form debe permitir varias líneas (un producto por línea,
      // con su precio de compra unitario) y subir una foto de la boleta. El
      // backend rechaza con 422 si `foto_boleta_url` viene vacía o si no hay
      // al menos una línea. Acá mandamos un placeholder para que la página
      // compile hasta el refactor; el botón "Registrar" no va a funcionar
      // contra el backend real en PR3a.
      await solicitar({
        foto_boleta_url: "https://placeholder.local/pendiente-pr3b",
        lineas: [
          { producto_id: Number(productoId), cantidad, precio_compra_unitario: 0 },
        ],
      });
      setMensaje("Ingreso registrado. Queda pendiente de aprobación del ADMIN.");
      setProductoId("");
      setCantidad(1);
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

  const columnas: Columna<IngresoMercaderia>[] = [
    {
      titulo: "Fecha",
      render: (i) => (
        <span className="whitespace-nowrap text-zinc-500">
          {i.created_at ? new Date(i.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      // TODO PR3b: la shape nueva es `lineas: DetalleSolicitud[]`. Acá
      // mostramos un resumen mientras se rehace la pantalla.
      titulo: "Producto",
      render: (i) => (
        <span className="font-medium text-zinc-800">
          {i.lineas.length === 1 ? `Producto #${i.lineas[0].producto_id}` : `${i.lineas.length} productos`}
        </span>
      ),
    },
    {
      titulo: "Cantidad",
      alinear: "derecha",
      render: (i) => <span className="tabular-nums">{i.cantidad_productos ?? 0}</span>,
    },
    {
      titulo: "Solicitado por",
      soloEscritorio: true,
      render: (i) => i.solicitado_por_nombre,
    },
    {
      titulo: "Estado",
      render: (i) => {
        // `estado` en backend es string; casteamos a `EstadoIngreso` para
        // indexar el mapa de tonos.
        const estado = i.estado as EstadoIngreso;
        const tono = TONO_ESTADO[estado] ?? "neutro";
        return (
          <div>
            <Badge tono={tono}>{i.estado}</Badge>
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
        descripcion="Registra lo que llega a tienda; el ADMIN lo aprueba y recién ahí suma al stock."
      />

      <Card titulo="Registrar ingreso" className="mb-4">
        <form onSubmit={(e) => void manejarSolicitar(e)} className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1">
            <Select
              label="Producto"
              value={productoId}
              onChange={(e) => setProductoId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Elige un producto…</option>
              {productos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre} (stock: {p.stock})
                </option>
              ))}
            </Select>
          </div>
          <div className="w-32">
            <Input
              label="Cantidad"
              type="number"
              min={1}
              value={cantidad}
              onChange={(e) => setCantidad(Number(e.target.value))}
            />
          </div>
          <Button type="submit" cargando={procesando} icono={<Truck className="h-4 w-4" aria-hidden />}>
            Registrar
          </Button>
        </form>
        {mensaje && (
          <div className="mt-3">
            <Alert tono="exito">{mensaje}</Alert>
          </div>
        )}
        {errorAccion && (
          <div className="mt-3">
            <Alert tono="peligro">{errorAccion}</Alert>
          </div>
        )}
      </Card>

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
                descripcion="Cuando llegue mercadería, regístrala aquí."
              />
            }
          />
        </Card>
      )}
    </div>
  );
}
