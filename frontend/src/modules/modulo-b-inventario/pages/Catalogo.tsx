// Catálogo (solo ADMIN): alta, edición y baja de productos, todo en la tabla.
//
// Se trabaja como en una planilla:
//   · "Nuevo producto" inserta una FILA VACÍA editable arriba de todo.
//   · El lápiz de una fila existente la vuelve editable en el lugar.
//   · En ambos casos el ícono pasa a ser un diskette; al guardarlo la fila
//     pregunta "¿Seguro que querés hacer este cambio?" con ✓ / ✗ y recién
//     entonces se aplica.
//
// La consulta de solo lectura del catálogo vive en el punto de venta.
import { useState } from "react";
import { Check, PackagePlus, Pencil, Plus, Save, Trash2, X } from "lucide-react";
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
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { PaginacionControles } from "../components/PaginacionControles";
import { useCategorias } from "../hooks/useCategorias";
import { useProductos } from "../hooks/useProductos";
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
  if (!fila.codigo.trim()) return "Escaneá o escribí un código.";
  if (!fila.nombre.trim()) return "El nombre no puede quedar vacío.";
  if (!(precio > 0)) return "El precio de venta debe ser mayor a 0.";
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
    void recargar({ page: nueva, page_size: pageSize });
  }

  function manejarCambioPageSize(nueva: number) {
    setPageSize(nueva);
    setPage(1);
    void recargar({ page: 1, page_size: nueva });
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Catálogo" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
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
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Código"
            className="w-32"
            autoFocus={esNueva(p)}
            placeholder="7750100000000"
            value={fila!.codigo}
            onChange={(e) => setFila({ ...fila!, codigo: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="font-mono text-xs text-zinc-500">{p.codigo}</span>
        ),
    },
    {
      titulo: "Producto",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Nombre"
            autoFocus={!esNueva(p)}
            placeholder="Arroz 5kg"
            value={fila!.nombre}
            onChange={(e) => setFila({ ...fila!, nombre: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="font-medium text-zinc-800">{p.nombre}</span>
        ),
    },
    {
      titulo: "Categoría",
      soloEscritorio: true,
      render: (p) =>
        enEdicion(p) ? (
          <Select
            aria-label="Categoría"
            className="w-40"
            value={fila!.categoria_id}
            onChange={(e) =>
              setFila({ ...fila!, categoria_id: e.target.value ? Number(e.target.value) : "" })
            }
            onKeyDown={teclasDeFila}
          >
            <option value="">Sin categoría</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </Select>
        ) : (
          (p.categoria_nombre ?? "—")
        ),
    },
    {
      titulo: "Precio",
      alinear: "derecha",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Precio de venta"
            className="w-24"
            type="number"
            step="0.10"
            min={0.01}
            placeholder="0.00"
            value={fila!.precio}
            onChange={(e) => setFila({ ...fila!, precio: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="tabular-nums">S/ {(p.precio_venta ?? p.precio).toFixed(2)}</span>
        ),
    },
    {
      titulo: "Stock",
      alinear: "derecha",
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label={esNueva(p) ? "Stock inicial" : "Stock"}
            className="w-20"
            type="number"
            min={0}
            value={fila!.stock}
            onChange={(e) => setFila({ ...fila!, stock: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="tabular-nums">{p.stock}</span>
        ),
    },
    {
      titulo: "Stock mín.",
      alinear: "derecha",
      soloEscritorio: true,
      render: (p) =>
        enEdicion(p) ? (
          <Input
            aria-label="Stock mínimo"
            className="w-20"
            type="number"
            min={0}
            value={fila!.stock_minimo}
            onChange={(e) => setFila({ ...fila!, stock_minimo: e.target.value })}
            onKeyDown={teclasDeFila}
          />
        ) : (
          <span className="tabular-nums">{p.stock_minimo}</span>
        ),
    },
    {
      titulo: "Estado",
      render: (p) =>
        esNueva(p) ? (
          <Badge tono="alerta">Nuevo</Badge>
        ) : (
          <Badge tono={p.activo ? "exito" : "neutro"}>{p.activo ? "Activo" : "Inactivo"}</Badge>
        ),
    },
    {
      titulo: "Acciones",
      alinear: "derecha",
      render: (p) => {
        // Paso 3: confirmación inline (✓ / ✗).
        if (enEdicion(p) && confirmando) {
          return (
            <div className="flex items-center justify-end gap-2">
              <span className="hidden text-xs text-zinc-600 sm:inline">
                {esNueva(p) ? "¿Creamos este producto?" : "¿Seguro que querés hacer este cambio?"}
              </span>
              <button
                type="button"
                onClick={() => void (esNueva(p) ? guardarAlta() : guardarEdicion(p))}
                disabled={procesando}
                title="Sí, guardar"
                aria-label="Confirmar"
                className="rounded border border-exito/30 bg-exito/10 p-1.5 text-exito hover:bg-exito/20 disabled:opacity-50"
              >
                <Check className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                onClick={() => setConfirmando(false)}
                disabled={procesando}
                title="No, volver a editar"
                aria-label="Cancelar"
                className="rounded border border-zinc-300 p-1.5 text-zinc-600 hover:bg-zinc-50 disabled:opacity-50"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
          );
        }
        // Paso 2: fila editable → el lápiz pasó a ser diskette.
        if (enEdicion(p)) {
          return (
            <div className="flex items-center justify-end gap-1">
              <button
                type="button"
                onClick={pedirConfirmacion}
                title="Guardar"
                aria-label="Guardar"
                className="rounded p-1.5 text-marca hover:bg-zinc-100"
              >
                <Save className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                onClick={cancelarEdicion}
                title="Descartar"
                aria-label="Descartar"
                className="rounded p-1.5 text-zinc-500 hover:bg-zinc-100"
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
              className="rounded p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 disabled:opacity-40"
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
              className="rounded p-1.5 text-zinc-500 hover:bg-red-50 hover:text-peligro disabled:opacity-40"
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
        descripcion="Se edita como una planilla: tocá el lápiz para modificar una fila."
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

      <Card sinPadding>
        <Table
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
    </div>
  );
}
