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
import {
  FormularioLineaIngreso,
  LINEA_INGRESO_VACIA,
  type LineaIngreso,
} from "../components/FormularioLineaIngreso";
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

const LINEA_VACIA: LineaIngreso = LINEA_INGRESO_VACIA;

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
      const vacia = actuales.findIndex((l) => !l.esNuevo && l.producto_id === null);
      const nueva: LineaIngreso = {
        ...LINEA_VACIA,
        producto_id: p.id,
        cantidad: 1,
        // Arranca con el costo conocido × 1 unidad; el cajero lo pisa con el
        // total real de la boleta.
        precio_compra_total: p.precio_compra_actual ?? 0,
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
    // La foto es opcional: no toda compra viene con boleta.
    if (lineas.length === 0) return "Agrega al menos una línea.";
    const codigosNuevos = new Set<string>();
    for (let i = 0; i < lineas.length; i++) {
      const l = lineas[i];
      if (l.esNuevo) {
        const codigo = l.nuevo_codigo.trim();
        if (!codigo) return `Línea ${i + 1}: falta el código de barras.`;
        if (!l.nuevo_nombre.trim()) return `Línea ${i + 1}: falta el nombre del producto.`;
        if (codigosNuevos.has(codigo))
          return `Línea ${i + 1}: el código ${codigo} está repetido en otra línea.`;
        codigosNuevos.add(codigo);
      } else if (!l.producto_id) {
        return `Línea ${i + 1}: elige un producto.`;
      }
      if (l.cantidad < 1) return `Línea ${i + 1}: la cantidad debe ser mayor a 0.`;
      if (l.precio_compra_total < 0) return `Línea ${i + 1}: el total no puede ser negativo.`;
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
      await solicitar({
        // Sin foto va cadena vacía: el backend la acepta así.
        foto_boleta_url: fotoUrl ?? "",
        proveedor_id: proveedorId === "" ? null : Number(proveedorId),
        lineas: lineas.map((l) => ({
          cantidad: l.cantidad,
          precio_compra_total: l.precio_compra_total,
          // Uno u otro, nunca los dos: es lo que valida el backend.
          producto_id: l.esNuevo ? null : l.producto_id,
          nuevo_codigo: l.esNuevo ? l.nuevo_codigo.trim() : null,
          nuevo_nombre: l.esNuevo ? l.nuevo_nombre.trim() : null,
          nuevo_categoria_id: l.esNuevo ? l.nuevo_categoria_id : null,
          margen_ganancia: l.esNuevo ? l.margen_ganancia : null,
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
      ancho: "135px",
      render: (i) => {
        if (!i.created_at) return <span className="text-zinc-400">—</span>;
        const d = new Date(i.created_at);
        const fecha = d.toLocaleDateString("es-PE");
        const hora = d.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        return (
          <div className="flex flex-col text-xs text-zinc-600">
            <span className="font-medium text-zinc-800">{fecha}</span>
            <span className="text-[11px] text-zinc-400">{hora}</span>
          </div>
        );
      },
    },
    {
      titulo: "Productos",
      ancho: "135px",
      render: (i) => (
        <div className="whitespace-nowrap">
          <span className="font-medium text-zinc-800">
            {i.cantidad_productos ?? i.lineas.length} unidades
          </span>
          <p className="text-xs text-zinc-500">{i.lineas.length} línea(s)</p>
        </div>
      ),
    },
    {
      titulo: "Monto",
      ancho: "100px",
      soloEscritorio: true,
      render: (i) => (
        <span className="tabular-nums font-medium">
          {i.monto_total != null ? `S/ ${i.monto_total.toFixed(2)}` : "—"}
        </span>
      ),
    },
    {
      titulo: "Solicitado por",
      ancho: "160px",
      soloEscritorio: true,
      render: (i) => <span className="block truncate font-medium text-zinc-800" title={i.solicitado_por_nombre}>{i.solicitado_por_nombre}</span>,
    },
    {
      titulo: "Estado",
      ancho: "130px",
      render: (i) => {
        const estado = String(i.estado);
        const tono = TONO_ESTADO[estado] ?? "neutro";
        return (
          <div>
            <Badge tono={tono}>{estado}</Badge>
            {i.motivo_rechazo && <p className="mt-1 text-xs text-zinc-500 line-clamp-2">{i.motivo_rechazo}</p>}
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
            className="w-full justify-center sm:w-auto"
          >
            {mostrarFormulario ? "Ocultar formulario" : "Nuevo ingreso"}
          </Button>
        }
      />

      {mostrarFormulario && (
        <Card titulo="Registrar ingreso" className="mb-4" descripcion="Carga una o más líneas con productos y costos. La foto de la boleta es opcional.">
          <div className="space-y-4">
            <SubirImagen
              carpeta="boletas"
              label="Foto de la boleta (opcional)"
              ayuda="Si tienes la boleta, adjúntala: JPG/PNG. Queda guardada en la solicitud."
              value={fotoUrl}
              onChange={setFotoUrl}
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
                  Escanea un código o busca por nombre
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
              <Button 
                type="button" 
                variante="secundario" 
                onClick={agregarLinea} 
                icono={<Plus className="h-4 w-4" aria-hidden />}
                className="w-full justify-center sm:w-auto"
              >
                Agregar línea
              </Button>
            </div>
            {mensaje && <Alert tono="exito">{mensaje}</Alert>}
            {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
            <div className="grid grid-cols-2 gap-2 sm:flex sm:justify-end">
              <Button variante="secundario" onClick={() => setMostrarFormulario(false)} className="w-full justify-center sm:w-auto">
                Cancelar
              </Button>
              <Button onClick={() => void manejarSolicitar()} cargando={procesando} icono={<Truck className="h-4 w-4" aria-hidden />} className="w-full justify-center sm:w-auto">
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
            minAncho="520px"
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
