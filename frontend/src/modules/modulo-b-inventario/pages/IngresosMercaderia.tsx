// Página para registrar nuevos ingresos de mercadería. El CAJERO solicita;
// el ADMIN los aprueba en la página de Aprobaciones.
//
// Escáner (misma regla que el POS): estando en esta pestaña, escanear un código
// —o escribir el nombre y dar Enter— busca el producto y lo agrega como línea.
// Si no existe, el aviso lo dice y se desvanece solo a los pocos segundos.
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, ScanBarcode, Truck } from "lucide-react";
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
import { FormularioLineaIngreso, type LineaIngreso } from "../components/FormularioLineaIngreso";
import { usePaginacionCursor } from "../../../shared/lib/use-paginacion-cursor";
import { PaginacionControles } from "../components/PaginacionControles";
import { SubirImagen } from "../components/SubirImagen";
import { useIngresos } from "../hooks/useIngresos";
import { useProveedores } from "../hooks/useProveedores";
import { useAvisoTemporal } from "../lib/useAvisoTemporal";
import { productosHttpAdapter } from "../services/productos.http-adapter";
import type { EstadoIngreso, FiltrosIngresos, Producto, SolicitudIngreso } from "../types";

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
  const { proveedores, error: errorProveedores } = useProveedores({ page_size: 100 });

  const [lineas, setLineas] = useState<LineaIngreso[]>([LINEA_VACIA]);
  // Buscador/lector: el escáner "tipea" acá y termina con Enter.
  const [busquedaProducto, setBusquedaProducto] = useState("");
  const [buscando, setBuscando] = useState(false);
  const inputEscaner = useRef<HTMLInputElement>(null);
  const { aviso, mostrar: mostrarAviso } = useAvisoTemporal();
  const [proveedorId, setProveedorId] = useState<number | "">("");
  const [fotoUrl, setFotoUrl] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState<EstadoIngreso | "">("");
  // Los cajeros registran ingresos mientras la lista se navega: con
  // `page`/OFFSET las filas nuevas corrían las páginas y se veían repetidas.
  const paginacion = usePaginacionCursor(20);
  const { page, pageSize, cursor, registrarRespuesta, reiniciar } = paginacion;

  const [mostrarFormulario, setMostrarFormulario] = useState(false);

  // Si la URL trae ?producto_id=NNN, pre-cargamos la primera línea.
  useEffect(() => {
    if (productoInicial) {
      setMostrarFormulario(true);
      setLineas([{ ...LINEA_VACIA, producto_id: Number(productoInicial) }]);
      // Limpiamos la query para no re-disparar al recargar la lista.
      const next = new URLSearchParams(searchParams);
      next.delete("producto_id");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productoInicial]);

  // Otro filtro ⇒ otro conjunto: los cursores acumulados dejan de valer.
  useEffect(() => {
    reiniciar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroEstado]);

  // Re-cargar lista cuando cambia filtro o paginación.
  useEffect(() => {
    const filtros: FiltrosIngresos = { page_size: pageSize };
    if (cursor) filtros.cursor = cursor;
    if (filtroEstado) filtros.estado = filtroEstado;
    void recargar(filtros);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroEstado, page, pageSize, cursor]);

  useEffect(() => {
    if (paginados) registrarRespuesta(paginados.siguiente_cursor);
  }, [paginados, registrarRespuesta]);

  // Estando en esta pestaña, el lector escribe donde esté el cursor: si el foco
  // quedó suelto (tras un clic en cualquier parte), lo devolvemos al buscador
  // para no perder el escaneo.
  useEffect(() => {
    function recuperarFoco(e: KeyboardEvent) {
      const objetivo = e.target as HTMLElement;
      const enCampo = ["INPUT", "TEXTAREA", "SELECT"].includes(objetivo.tagName);
      if (!enCampo && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        inputEscaner.current?.focus();
      }
    }
    window.addEventListener("keydown", recuperarFoco);
    return () => window.removeEventListener("keydown", recuperarFoco);
  }, []);

  /** Suma el producto a las líneas: si ya está, +1; si hay una línea vacía, la usa. */
  function agregarProductoALinea(p: Producto) {
    setLineas((actuales) => {
      const yaEsta = actuales.findIndex((l) => l.producto_id === p.id);
      if (yaEsta !== -1) {
        return actuales.map((l, i) => (i === yaEsta ? { ...l, cantidad: l.cantidad + 1 } : l));
      }
      const vacia = actuales.findIndex((l) => l.producto_id === null);
      const nueva: LineaIngreso = {
        producto_id: p.id,
        cantidad: 1,
        precio_compra_unitario: p.precio_compra_actual ?? 0,
      };
      if (vacia !== -1) return actuales.map((l, i) => (i === vacia ? nueva : l));
      return [...actuales, nueva];
    });
    mostrarAviso(`"${p.nombre}" agregado a la solicitud.`, "exito");
  }

  /** Enter en el buscador = fin de un escaneo o de una búsqueda por nombre. */
  async function buscarYAgregar() {
    const texto = busquedaProducto.trim();
    if (!texto || buscando) return;
    setBuscando(true);
    try {
      // 1) por código exacto (es lo que manda el lector)
      try {
        const porCodigo = await productosHttpAdapter.buscar(texto);
        const producto = Array.isArray(porCodigo) ? porCodigo[0] : porCodigo;
        if (producto) {
          agregarProductoALinea(producto);
          setBusquedaProducto("");
          return;
        }
      } catch {
        // 404: no hay ningún producto con ese código. Probamos por nombre.
      }
      // 2) por nombre
      const porNombre = await productosHttpAdapter.buscar(undefined, texto);
      const coincidencias = Array.isArray(porNombre) ? porNombre : [porNombre];
      if (coincidencias.length === 1) {
        agregarProductoALinea(coincidencias[0]);
        setBusquedaProducto("");
      } else if (coincidencias.length > 1) {
        mostrarAviso(
          `Hay ${coincidencias.length} productos que coinciden con "${texto}". Escanea el código o elígelo en la línea.`,
          "alerta",
        );
      } else {
        mostrarAviso(`No existe ningún producto con "${texto}".`, "peligro");
      }
    } catch {
      mostrarAviso(`No existe ningún producto con "${texto}".`, "peligro");
    } finally {
      setBuscando(false);
      inputEscaner.current?.focus();
    }
  }

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
    if (!fotoUrl) return "Sube la foto de la boleta (obligatoria).";
    if (lineas.length === 0) return "Agrega al menos una línea.";
    for (let i = 0; i < lineas.length; i++) {
      const l = lineas[i];
      if (!l.producto_id) return `Línea ${i + 1}: elige un producto.`;
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
      setMensaje("Ingreso registrado. Queda pendiente de la aprobación del administrador.");
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
          <ModuloPendiente modulo="inventario" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<SolicitudIngreso>[] = [
    {
      titulo: "Fecha",
      ancho: "20%",
      render: (i) => (
        <span className="whitespace-nowrap text-zinc-500">
          {i.created_at ? new Date(i.created_at).toLocaleString("es-PE") : "—"}
        </span>
      ),
    },
    {
      titulo: "Productos",
      ancho: "18%",
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
      ancho: "14%",
      soloEscritorio: true,
      render: (i) => (
        <span className="tabular-nums font-medium">
          {i.monto_total != null ? `S/ ${i.monto_total.toFixed(2)}` : "—"}
        </span>
      ),
    },
    {
      titulo: "Solicitado por",
      ancho: "26%",
      soloEscritorio: true,
      render: (i) => <span className="block truncate font-medium text-zinc-800" title={i.solicitado_por_nombre}>{i.solicitado_por_nombre}</span>,
    },
    {
      titulo: "Estado",
      ancho: "22%",
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
        descripcion="Registra lo que llega a tienda; el ADMIN lo aprueba y recién ahí suma al stock."
        acciones={
          <Button
            icono={mostrarFormulario ? undefined : <Plus className="h-4 w-4" aria-hidden />}
            variante={mostrarFormulario ? "secundario" : "primario"}
            onClick={() => setMostrarFormulario(!mostrarFormulario)}
          >
            {mostrarFormulario ? "Ocultar formulario" : "Nuevo ingreso"}
          </Button>
        }
      />

      {mostrarFormulario && (
        <Card titulo="Registrar ingreso" className="mb-4" descripcion="Sube la foto de la boleta y una o más líneas con productos y costos.">
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
            {errorProveedores && (
              <Alert tono="peligro">No se pudieron cargar los proveedores: {errorProveedores}</Alert>
            )}
            <div className="space-y-3">
              {/* Buscador + lector: agrega la línea sin tocar el mouse. */}
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700">
                  Escaneá un código o buscá por nombre
                </label>
                <div className="relative">
                  <ScanBarcode
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
                    aria-hidden
                  />
                  <Input
                    ref={inputEscaner}
                    className="pl-9"
                    autoFocus
                    placeholder="El lector agrega el producto automáticamente…"
                    value={busquedaProducto}
                    onChange={(e) => setBusquedaProducto(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        void buscarYAgregar();
                      }
                    }}
                  />
                </div>
                {aviso && (
                  <div className="mt-2">
                    <Alert tono={aviso.tono}>{aviso.texto}</Alert>
                  </div>
                )}
              </div>
              {lineas.map((l, i) => (
                <FormularioLineaIngreso
                  key={i}
                  linea={l}
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
            <div className="flex justify-end gap-2">
              <Button variante="secundario" onClick={() => setMostrarFormulario(false)}>
                Cancelar
              </Button>
              <Button onClick={() => void manejarSolicitar()} cargando={procesando} icono={<Truck className="h-4 w-4" aria-hidden />}>
                Registrar ingreso
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <Select
          label="Filtrar por estado"
          value={filtroEstado}
          onChange={(e) => {
            setFiltroEstado(e.target.value as EstadoIngreso | "");
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
            minAncho="100%"
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
            onCambiarPage={paginacion.onCambiarPage}
            onCambiarPageSize={paginacion.onCambiarPageSize}
            etiqueta="ingresos"
          />
        </Card>
      )}
    </div>
  );
}
