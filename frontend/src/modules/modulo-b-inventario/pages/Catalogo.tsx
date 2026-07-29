// Catálogo (solo ADMIN): alta, edición y baja de productos, todo en la tabla.
//
// Se trabaja como en una planilla:
//   · "Nuevo producto" inserta una FILA VACÍA editable arriba de todo.
//   · El lápiz de una fila existente la vuelve editable en el lugar.
//   · En ambos casos el ícono pasa a ser un diskette; al guardarlo la fila
//     pregunta "¿Seguro que quieres hacer este cambio?" con ✓ / ✗ y recién
//     entonces se aplica.
//
// La consulta de solo lectura del catálogo vive en el punto de venta.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, PackagePlus, Pencil, Plus, Save, ScanBarcode, Search, SlidersHorizontal, Trash2, X } from "lucide-react";
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
  Select,
  SelectorCategoriaModal,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { ModalConfirmacion } from "../components/ModalConfirmacion";
import { PaginacionControles } from "../components/PaginacionControles";
import { useCategorias } from "../hooks/useCategorias";
import { useProductos } from "../hooks/useProductos";
import { productosHttpAdapter } from "../services/productos.http-adapter";
import type { NuevoProducto, Producto } from "../types";

/** Id ficticio de la fila de alta (no existe en el backend). */
const ID_NUEVA = -1;

/** Valores editables de una fila (alta o edición). */
interface FilaEditada {
  codigo: string;
  nombre: string;
  categoria_id: number | "";
  precio: string;
  stock: string;
  stock_minimo: string;
}

const FILA_VACIA: FilaEditada = {
  codigo: "",
  nombre: "",
  categoria_id: "",
  precio: "",
  stock: "0",
  stock_minimo: "0",
};

function filaDesde(p: Producto): FilaEditada {
  return {
    codigo: p.codigo,
    nombre: p.nombre,
    categoria_id: p.categoria_id ?? "",
    precio: String(p.precio_venta ?? p.precio),
    stock: String(p.stock),
    stock_minimo: String(p.stock_minimo),
  };
}

/** Fila fantasma que ocupa el lugar del alta dentro de la tabla. */
const PRODUCTO_NUEVO = {
  id: ID_NUEVA,
  codigo: "",
  nombre: "",
  categoria_id: null,
  categoria_nombre: null,
  precio: 0,
  precio_compra_actual: 0,
  stock: 0,
  stock_minimo: 0,
  activo: true,
  es_codigo_interno: false,
} as unknown as Producto;

/** Valida los campos comunes al alta y a la edición. Devuelve el error o null. */
function validar(fila: FilaEditada): string | null {
  const precio = Number(fila.precio);
  const stock = Number(fila.stock);
  const stockMinimo = Number(fila.stock_minimo);
  if (!fila.codigo.trim()) return "Escanea o escribe un código.";
  if (!fila.nombre.trim()) return "El nombre no puede quedar vacío.";
  if (!(precio > 0)) return "El precio de venta debe ser mayor a 0.";
  if (Math.round(precio * 100) % 10 !== 0)
    return "El precio de venta debe ser un múltiplo de S/ 0.10 (ej. 2.50, 3.80).";
  if (!Number.isInteger(stock) || stock < 0) return "El stock debe ser un entero no negativo.";
  if (!Number.isInteger(stockMinimo) || stockMinimo < 0)
    return "El stock mínimo debe ser un entero no negativo.";
  return null;
}

export default function Catalogo() {
  const {
    productos,
    paginados,
    cargando,
    error,
    noDisponible,
    recargar,
    crear,
    actualizar,
    cambiarPrecio,
    ajustarStock,
    eliminar,
  } = useProductos();
  const { categorias, crear: crearCategoria } = useCategorias();

  // Alta de categoría: hasta ahora sólo se podían crear por BD. El único
  // componente que las creaba (`SelectorCategoria`) quedó huérfano cuando esta
  // página reemplazó a GestionProductos.
  const [nuevaCategoria, setNuevaCategoria] = useState<string | null>(null);
  const [creandoCategoria, setCreandoCategoria] = useState(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  /** Fila en edición: `ID_NUEVA` = alta; un id real = edición de esa fila. */
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [fila, setFila] = useState<FilaEditada | null>(null);
  /** La fila está esperando el ✓ / ✗ de confirmación. */
  const [confirmando, setConfirmando] = useState(false);
  /** Producto en espera de confirmación de baja. */
  const [porEliminar, setPorEliminar] = useState<Producto | null>(null);

  // --- Buscador y Filtros sobre la tabla con autocompletado en tiempo real ---
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busquedaAplicada, setBusquedaAplicada] = useState("");
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false);
  const [indiceSugerencia, setIndiceSugerencia] = useState(0);
  const [todosLosProductos, setTodosLosProductos] = useState<Producto[]>([]);
  const inputBusquedaRef = useRef<HTMLInputElement>(null);

  // Filtros adicionales en modal
  const [modalFiltrosAbierto, setModalFiltrosAbierto] = useState(false);
  const [filtroCategoriaId, setFiltroCategoriaId] = useState<number | "">("");
  const [filtroEstado, setFiltroEstado] = useState<"todos" | "activos" | "inactivos">("todos");
  const [filtroStock, setFiltroStock] = useState<"todos" | "con_stock" | "sin_stock" | "bajo_minimo">("todos");

  const filtrosActivosCount = useMemo(() => {
    let count = 0;
    if (filtroCategoriaId !== "") count++;
    if (filtroEstado !== "todos") count++;
    if (filtroStock !== "todos") count++;
    return count;
  }, [filtroCategoriaId, filtroEstado, filtroStock]);

  // Cargar catálogo completo para autocompletar sugerencias en tiempo real
  const recargarSugerencias = useCallback(() => {
    void productosHttpAdapter
      .listar({ page_size: 250 })
      .then((resp) => {
        setTodosLosProductos(resp.items ?? []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    recargarSugerencias();
  }, [recargarSugerencias]);

  // Coincidencias en tiempo real (autocompletado mientras escribe)
  const sugerencias = useMemo(() => {
    const q = busquedaInput.trim().toLowerCase();
    if (!q) return [];
    return todosLosProductos
      .filter((p) => {
        const codigoMatch = p.codigo?.toLowerCase().includes(q);
        const palabras = p.nombre.toLowerCase().split(/\s+/);
        const palabraMatch = palabras.some((w) => w.startsWith(q));
        const nombreMatch = p.nombre.toLowerCase().includes(q);
        return codigoMatch || palabraMatch || nombreMatch;
      })
      .slice(0, 8);
  }, [todosLosProductos, busquedaInput]);

  function construirFiltros(override?: { page?: number; pageSize?: number; search?: string }) {
    const p = override?.page ?? 1;
    const ps = override?.pageSize ?? pageSize;
    const s = override?.search !== undefined ? override.search : busquedaAplicada;

    return {
      page: p,
      page_size: ps,
      search: s || undefined,
      categoria_id: filtroCategoriaId === "" ? undefined : Number(filtroCategoriaId),
      activo: filtroEstado === "activos" ? true : filtroEstado === "inactivos" ? false : undefined,
      solo_con_stock: filtroStock === "con_stock" ? true : undefined,
      sin_stock: filtroStock === "sin_stock" ? true : undefined,
      solo_bajo_minimo: filtroStock === "bajo_minimo" ? true : undefined,
    };
  }

  function aplicarBusqueda(texto?: string) {
    const query = (texto !== undefined ? texto : busquedaInput).trim();
    setBusquedaAplicada(query);
    setMostrarSugerencias(false);
    setPage(1);
    void recargar(construirFiltros({ page: 1, search: query }));
  }

  function seleccionarSugerencia(p: Producto) {
    setBusquedaInput(p.nombre);
    aplicarBusqueda(p.nombre);
  }

  function limpiarBusqueda() {
    setBusquedaInput("");
    setBusquedaAplicada("");
    setMostrarSugerencias(false);
    setPage(1);
    void recargar(construirFiltros({ page: 1, search: "" }));
  }

  function aplicarFiltros() {
    setModalFiltrosAbierto(false);
    setPage(1);
    void recargar(construirFiltros({ page: 1 }));
  }

  function limpiarFiltros() {
    setFiltroCategoriaId("");
    setFiltroEstado("todos");
    setFiltroStock("todos");
    setModalFiltrosAbierto(false);
    setPage(1);
    void recargar({
      page: 1,
      page_size: pageSize,
      search: busquedaAplicada || undefined,
    });
  }

  function empezarAlta() {
    setErrorAccion(null);
    setMensaje(null);
    setConfirmando(false);
    setEditandoId(ID_NUEVA);
    setFila({ ...FILA_VACIA });
  }

  function empezarEdicion(p: Producto) {
    setErrorAccion(null);
    setMensaje(null);
    setConfirmando(false);
    setEditandoId(p.id);
    setFila(filaDesde(p));
  }

  function cancelarEdicion() {
    setEditandoId(null);
    setFila(null);
    setConfirmando(false);
    setErrorAccion(null);
  }

  function pedirConfirmacion() {
    if (!fila) return;
    const problema = validar(fila);
    if (problema) {
      setErrorAccion(problema);
      return;
    }
    setErrorAccion(null);
    setConfirmando(true);
  }

  /** Alta: una sola llamada con todo lo que trae la fila. */
  async function guardarAlta() {
    if (!fila) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      const nuevo: NuevoProducto = {
        codigo: fila.codigo.trim(),
        nombre: fila.nombre.trim(),
        categoria_id: fila.categoria_id === "" ? null : fila.categoria_id,
        precio_venta: Number(fila.precio),
        precio_compra_actual: 0,
        stock_inicial: Number(fila.stock),
        stock_minimo: Number(fila.stock_minimo),
        es_codigo_interno: false,
      };
      await crear(nuevo);
      setMensaje(`Producto '${nuevo.nombre}' creado.`);
      cancelarEdicion();
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
      setConfirmando(false);
    } finally {
      setProcesando(false);
    }
  }

  /** Edición: cada campo va a su endpoint (datos, precio y ajuste de stock). */
  async function guardarEdicion(p: Producto) {
    if (!fila) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      const categoriaNueva = fila.categoria_id === "" ? null : fila.categoria_id;
      const precio = Number(fila.precio);
      const stock = Number(fila.stock);
      const stockMinimo = Number(fila.stock_minimo);

      if (
        fila.codigo.trim() !== p.codigo ||
        fila.nombre.trim() !== p.nombre ||
        categoriaNueva !== p.categoria_id ||
        stockMinimo !== p.stock_minimo
      ) {
        await actualizar(p.id, {
          codigo: fila.codigo.trim(),
          nombre: fila.nombre.trim(),
          categoria_id: categoriaNueva,
          stock_minimo: stockMinimo,
        });
      }
      if (precio !== (p.precio_venta ?? p.precio)) {
        await cambiarPrecio(p.id, { precio_venta: precio });
      }
      // El stock no se "setea": se ajusta con un delta que deja su asiento en
      // `movimientos_inventario` (tipo='ajuste') con el motivo.
      if (stock !== p.stock) {
        await ajustarStock(p.id, {
          delta: stock - p.stock,
          motivo: "Ajuste manual desde el catálogo",
        });
      }
      await recargar({ page, page_size: pageSize });
      setMensaje(`'${fila.nombre.trim()}' actualizado.`);
      cancelarEdicion();
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
      setConfirmando(false);
    } finally {
      setProcesando(false);
    }
  }

  async function confirmarBaja() {
    if (!porEliminar) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await eliminar(porEliminar.id, {});
      setMensaje(`'${porEliminar.nombre}' fue eliminado del catálogo.`);
      setPorEliminar(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  async function guardarCategoria() {
    const nombre = (nuevaCategoria ?? "").trim();
    if (!nombre) return;
    setCreandoCategoria(true);
    setErrorAccion(null);
    try {
      await crearCategoria({ nombre });
      setMensaje(`Categoría '${nombre}' creada.`);
      setNuevaCategoria(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setCreandoCategoria(false);
    }
  }

  function manejarCambioPage(nueva: number) {
    setPage(nueva);
    void recargar(construirFiltros({ page: nueva }));
  }

  function manejarCambioPageSize(nueva: number) {
    setPageSize(nueva);
    setPage(1);
    void recargar(construirFiltros({ page: 1, pageSize: nueva }));
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Catálogo" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando catálogo…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const esNueva = (p: Producto) => p.id === ID_NUEVA;
  const enEdicion = (p: Producto) => editandoId === p.id && fila !== null;
  /** Enter guarda, Escape descarta: se edita sin soltar el teclado. */
  function teclasDeFila(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      pedirConfirmacion();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelarEdicion();
    }
  }

  const columnas: Columna<Producto>[] = [
    {
      titulo: "Código",
      ancho: "135px",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Código"
            className="w-full min-w-0"
            autoFocus={esNueva(p)}
            placeholder="7750100000000"
            value={fila!.codigo}
            onChange={(e) => setFila({ ...fila!, codigo: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="font-mono text-xs text-zinc-500 truncate block">{p.codigo}</span>
        ),
    },
    {
      titulo: "Producto",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Nombre"
            className="w-full min-w-0"
            autoFocus={!esNueva(p)}
            placeholder="Arroz 5kg"
            value={fila!.nombre}
            onChange={(e) => setFila({ ...fila!, nombre: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="font-medium text-zinc-800 leading-snug">{p.nombre}</span>
        ),
    },
    {
      titulo: "Categoría",
      ancho: "150px",
      soloEscritorio: true,
      render: (p) =>
        enEdicion(p) ? (
          <SelectorCategoriaModal
            categorias={categorias}
            className="w-full min-w-0"
            valor={fila!.categoria_id}
            onSeleccionar={(id) => setFila({ ...fila!, categoria_id: id })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="text-zinc-600">{p.categoria_nombre ?? "—"}</span>
        ),
    },
    {
      titulo: "Precio",
      ancho: "95px",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Precio de venta"
            className="w-full min-w-0"
            type="number"
            step="0.10"
            min={0.10}
            placeholder="0.00"
            value={fila!.precio}
            onChange={(e) => setFila({ ...fila!, precio: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="tabular-nums font-medium">S/ {(p.precio_venta ?? p.precio).toFixed(2)}</span>
        ),
    },
    {
      titulo: "Stock",
      ancho: "80px",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label={esNueva(p) ? "Stock inicial" : "Stock"}
            className="w-full min-w-0"
            type="number"
            min={0}
            value={fila!.stock}
            onChange={(e) => setFila({ ...fila!, stock: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="tabular-nums font-medium">{p.stock}</span>
        ),
    },
    {
      titulo: "Stock mín.",
      ancho: "85px",
      soloEscritorio: true,
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Stock mínimo"
            className="w-full min-w-0"
            type="number"
            min={0}
            value={fila!.stock_minimo}
            onChange={(e) => setFila({ ...fila!, stock_minimo: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="tabular-nums font-medium">{p.stock_minimo}</span>
        ),
    },
    {
      titulo: "Estado",
      ancho: "95px",
      render: (p) =>
        esNueva(p) ? (
          <Badge tono="alerta">Nuevo</Badge>
        ) : (
          <Badge tono={p.activo ? "exito" : "neutro"}>{p.activo ? "Activo" : "Inactivo"}</Badge>
        ),
    },
    {
      titulo: "Acciones",
      ancho: "95px",
      alinear: "derecha",
      render: (p) => {
        // Paso 2: fila editable → el lápiz pasó a ser diskette.
        if (enEdicion(p)) {
          return (
            <div className="flex items-center justify-end gap-1">
              <button
                type="button"
                onClick={pedirConfirmacion}
                title="Guardar"
                aria-label="Guardar"
                className="inline-flex min-h-tactil min-w-11 items-center justify-center rounded p-1.5 sm:min-h-0 sm:min-w-0 text-marca hover:bg-zinc-100"
              >
                <Save className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                onClick={cancelarEdicion}
                title="Descartar"
                aria-label="Descartar"
                className="inline-flex min-h-tactil min-w-11 items-center justify-center rounded p-1.5 sm:min-h-0 sm:min-w-0 text-zinc-500 hover:bg-zinc-100"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
          );
        }
        // Paso 1: fila de solo lectura.
        return (
          <div className="flex items-center justify-end gap-1">
            <button
              type="button"
              onClick={() => empezarEdicion(p)}
              disabled={editandoId !== null}
              title="Editar fila"
              aria-label={`Editar ${p.nombre}`}
              className="inline-flex min-h-tactil min-w-11 items-center justify-center rounded p-1.5 sm:min-h-0 sm:min-w-0 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 disabled:opacity-40"
            >
              <Pencil className="h-4 w-4" aria-hidden />
            </button>
            <button
              type="button"
              onClick={() => {
                setErrorAccion(null);
                setPorEliminar(p);
              }}
              disabled={editandoId !== null}
              title="Eliminar producto"
              aria-label={`Eliminar ${p.nombre}`}
              className="inline-flex min-h-tactil min-w-11 items-center justify-center rounded p-1.5 sm:min-h-0 sm:min-w-0 text-zinc-500 hover:bg-red-50 hover:text-peligro disabled:opacity-40"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </div>
        );
      },
    },
  ];

  // La fila de alta va arriba de todo, dentro de la misma tabla.
  const filas = editandoId === ID_NUEVA ? [PRODUCTO_NUEVO, ...productos] : productos;

  return (
    <div>
      <PageHeader
        titulo="Catálogo"
        descripcion="Se edita como una planilla: toca el lápiz para modificar una fila."
        acciones={
          <div className="flex flex-wrap gap-2">
            <Button
              variante="secundario"
              onClick={() => setNuevaCategoria("")}
              disabled={nuevaCategoria !== null}
              icono={<Plus className="h-4 w-4" aria-hidden />}
            >
              Nueva categoría
            </Button>
            <Button
              onClick={empezarAlta}
              disabled={editandoId !== null}
              icono={<Plus className="h-4 w-4" aria-hidden />}
            >
              Nuevo producto
            </Button>
          </div>
        }
      />

      {/* Alta de categoría en línea: mismo criterio que el resto de la página
          (se edita en el lugar, sin modales). Enter guarda, Escape descarta. */}
      {nuevaCategoria !== null && (
        <Card className="mb-4">
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-56 flex-1">
              <Input
                label="Nueva categoría"
                placeholder="ej. Abarrotes"
                value={nuevaCategoria}
                autoFocus
                maxLength={80}
                onChange={(e) => setNuevaCategoria(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void guardarCategoria();
                  }
                  if (e.key === "Escape") setNuevaCategoria(null);
                }}
              />
            </div>
            <Button
              onClick={() => void guardarCategoria()}
              cargando={creandoCategoria}
              disabled={!nuevaCategoria.trim()}
            >
              Guardar
            </Button>
            <Button
              variante="secundario"
              onClick={() => setNuevaCategoria(null)}
              disabled={creandoCategoria}
            >
              Cancelar
            </Button>
          </div>
        </Card>
      )}

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

      {/* Buscador + Botón de Filtros sobre la tabla */}
      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <div className="relative flex-1 min-w-[260px]">
          <div className="relative flex w-full items-center rounded-xl border border-zinc-200 bg-white p-1 shadow-sm transition-all focus-within:border-zinc-400 focus-within:ring-2 focus-within:ring-marca/20">
            <ScanBarcode className="pointer-events-none absolute left-3.5 h-5 w-5 text-zinc-400" />
            <input
              ref={inputBusquedaRef}
              type="text"
              className="w-full bg-transparent py-2 pl-11 pr-32 text-sm text-zinc-900 focus:outline-none placeholder:text-zinc-400"
              placeholder="Escanea un código o busca por nombre…"
              value={busquedaInput}
              onChange={(e) => {
                setBusquedaInput(e.target.value);
                setMostrarSugerencias(true);
                setIndiceSugerencia(0);
              }}
              onFocus={() => setMostrarSugerencias(true)}
              onBlur={() => setTimeout(() => setMostrarSugerencias(false), 200)}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setIndiceSugerencia((prev) => Math.min(prev + 1, sugerencias.length - 1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setIndiceSugerencia((prev) => Math.max(prev - 1, 0));
                } else if (e.key === "Enter") {
                  e.preventDefault();
                  if (mostrarSugerencias && sugerencias[indiceSugerencia]) {
                    seleccionarSugerencia(sugerencias[indiceSugerencia]);
                  } else {
                    aplicarBusqueda();
                  }
                } else if (e.key === "Escape") {
                  setMostrarSugerencias(false);
                  if (busquedaInput || busquedaAplicada) {
                    limpiarBusqueda();
                  }
                }
              }}
              role="combobox"
              aria-expanded={mostrarSugerencias && sugerencias.length > 0}
            />
            <div className="absolute right-1.5 flex items-center gap-1.5">
              {(busquedaInput || busquedaAplicada) && (
                <>
                  <button
                    type="button"
                    onClick={limpiarBusqueda}
                    title="Limpiar búsqueda"
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-zinc-100 text-zinc-500 hover:bg-zinc-200 hover:text-zinc-700 transition-all active:scale-95"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                  <div className="h-4 w-px bg-zinc-200" />
                </>
              )}
              <Button
                compacto
                onClick={() => aplicarBusqueda()}
                icono={<Search className="h-4 w-4" aria-hidden />}
              >
                Buscar
              </Button>
            </div>
          </div>

          {/* Desplegable de autocompletado en tiempo real */}
          {mostrarSugerencias && busquedaInput.trim().length > 0 && sugerencias.length > 0 && (
            <ul
              role="listbox"
              className="absolute left-0 right-0 z-30 mt-1.5 max-h-72 w-full overflow-y-auto rounded-xl border shadow-xl"
              style={{
                background: "var(--ui-fondo-panel)",
                borderColor: "var(--ui-borde)",
              }}
            >
              {sugerencias.map((p, idx) => {
                const esSeleccionado = idx === indiceSugerencia;
                return (
                  <li key={p.id} role="option" aria-selected={esSeleccionado}>
                    <button
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        seleccionarSugerencia(p);
                      }}
                      onMouseEnter={() => setIndiceSugerencia(idx)}
                      className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm transition-colors"
                      style={{
                        background: esSeleccionado ? "var(--ui-item-activo)" : "transparent",
                        color: "var(--ui-texto-principal)",
                      }}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-medium">{p.nombre}</span>
                          {p.categoria_nombre && (
                            <Badge tono="neutro">
                              {p.categoria_nombre}
                            </Badge>
                          )}
                        </div>
                        <span className="font-mono text-xs opacity-60">{p.codigo}</span>
                      </div>
                      <div className="text-right shrink-0 text-xs font-semibold">
                        <span>S/ {(p.precio_venta ?? p.precio).toFixed(2)}</span>
                        <span className="block text-[10px] font-normal opacity-70">
                          Stock: {p.stock}
                        </span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <Button
          type="button"
          variante={filtrosActivosCount > 0 ? "primario" : "secundario"}
          onClick={() => setModalFiltrosAbierto(true)}
          icono={<SlidersHorizontal className="h-4 w-4" aria-hidden />}
          className="shrink-0"
          title="Filtros avanzados"
        >
          <span className="hidden sm:inline">Filtros</span>
          {filtrosActivosCount > 0 && (
            <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-white px-1 text-[11px] font-bold text-marca shadow-xs">
              {filtrosActivosCount}
            </span>
          )}
        </Button>
      </div>

      <Card sinPadding>
        <Table
          minAncho="850px"
          columnas={columnas}
          filas={filas}
          claveDe={(p) => p.id}
          vacio={
            <EmptyState
              icono={PackagePlus}
              titulo="Sin productos"
              descripcion="Crea el primer producto del catálogo."
              accion={<Button onClick={empezarAlta}>Nuevo producto</Button>}
            />
          }
        />
        <PaginacionControles
          paginados={paginados}
          page={page}
          pageSize={pageSize}
          onCambiarPage={manejarCambioPage}
          onCambiarPageSize={manejarCambioPageSize}
          etiqueta="productos"
        />
      </Card>

      {/* Guardar producto: confirmación en modal */}
      <ModalConfirmacion
        abierto={confirmando}
        titulo={editandoId === ID_NUEVA ? "Crear producto" : "Guardar cambios"}
        mensaje={
          editandoId === ID_NUEVA
            ? `¿Creamos el producto "${fila?.nombre.trim() || "nuevo"}" en el catálogo?`
            : `¿Guardar los cambios en "${fila?.nombre.trim() || "este producto"}"?`
        }
        textoConfirmar={editandoId === ID_NUEVA ? "Sí, crear" : "Sí, guardar"}
        cargando={procesando}
        alCancelar={() => setConfirmando(false)}
        alConfirmar={() => {
          const esNuevo = editandoId === ID_NUEVA;
          const productoActual = productos.find((p) => p.id === editandoId) ?? null;
          if (esNuevo) void guardarAlta();
          else if (productoActual) void guardarEdicion(productoActual);
        }}
      />

      {/* Baja de producto: confirmación explícita */}
      <Modal
        abierto={porEliminar !== null}
        titulo="Eliminar producto"
        alCerrar={() => setPorEliminar(null)}
        pie={
          <>
            <button
              type="button"
              onClick={() => setPorEliminar(null)}
              disabled={procesando}
              className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
            >
              No, cancelar
            </button>
            <button
              type="button"
              onClick={() => void confirmarBaja()}
              disabled={procesando}
              className="inline-flex min-h-tactil items-center justify-center gap-2 rounded-lg bg-peligro px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
            >
              <Check className="h-4 w-4" aria-hidden />
              Sí, eliminar
            </button>
          </>
        }
      >
        <div className="space-y-2 text-sm text-zinc-700">
          <p>
            ¿Seguro que querés eliminar <strong>{porEliminar?.nombre}</strong> (
            {porEliminar?.codigo})?
          </p>
          <p className="text-zinc-500">
            Deja de aparecer en el catálogo y en el punto de venta. Su historial de
            movimientos y ventas se conserva.
          </p>
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
        </div>
      </Modal>

      {/* Modal de Filtros Avanzados */}
      <Modal
        abierto={modalFiltrosAbierto}
        titulo="Filtros de catálogo"
        alCerrar={() => setModalFiltrosAbierto(false)}
        pie={
          <div className="flex w-full items-center justify-between gap-2">
            <Button
              variante="secundario"
              onClick={limpiarFiltros}
              disabled={filtrosActivosCount === 0}
            >
              Limpiar filtros
            </Button>
            <Button onClick={() => aplicarFiltros()}>
              Aplicar filtros
            </Button>
          </div>
        }
      >
        <div className="space-y-5 py-1">
          {/* Categoría */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-700">
              Categoría
            </label>
            <SelectorCategoriaModal
              categorias={categorias}
              valor={filtroCategoriaId}
              onSeleccionar={(id) => setFiltroCategoriaId(id)}
              placeholderSinCategoria="Todas las categorías"
            />
          </div>

          {/* Estado de producto */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-700">
              Estado del producto
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "todos", label: "Todos" },
                { id: "activos", label: "Activos" },
                { id: "inactivos", label: "Inactivos" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setFiltroEstado(opt.id as any)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                    filtroEstado === opt.id
                      ? "border-marca bg-marca/10 font-semibold text-marca ring-1 ring-marca"
                      : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Estado de stock */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-700">
              Nivel de stock
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: "todos", label: "Todo el stock" },
                { id: "con_stock", label: "Con stock disponible" },
                { id: "sin_stock", label: "Sin stock (Agotados)" },
                { id: "bajo_minimo", label: "Stock crítico (Bajo mín.)" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setFiltroStock(opt.id as any)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                    filtroStock === opt.id
                      ? "border-marca bg-marca/10 font-semibold text-marca ring-1 ring-marca"
                      : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
