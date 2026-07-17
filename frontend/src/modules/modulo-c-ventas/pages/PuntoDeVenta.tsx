// Página del punto de venta (POS): registrar una venta. Pensada para uso
// táctil: productos como botones grandes a la izquierda, carrito a la derecha.
// El catálogo viene del módulo B (puerto de productos).
//
// Escáner (HU-C01): el lector de barras/QR emula un teclado y termina con Enter.
// El buscador mantiene el foco (se recupera solo si se pierde), y al recibir
// Enter con un código exacto agrega el producto al carrito al instante.
import { useEffect, useMemo, useRef, useState } from "react";
import { Minus, Plus, ScanBarcode, Search, ShoppingCart, Trash2 } from "lucide-react";
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
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useProductos } from "../../modulo-b-inventario/hooks/useProductos";
import type { Producto } from "../../modulo-b-inventario/types";
import { useCaja } from "../hooks/useCaja";
import { useVenta } from "../hooks/useVenta";
import type { ItemVenta, MetodoPago } from "../types";

const METODOS_PAGO: MetodoPago[] = ["EFECTIVO", "YAPE", "PLIN", "TARJETA"];

export default function PuntoDeVenta() {
  const { productos, cargando, noDisponible, recargar: recargarProductos } = useProductos();
  const { turno, noDisponible: cajaNoDisponible } = useCaja();
  const { registrar } = useVenta();

  const [busqueda, setBusqueda] = useState("");
  const [carrito, setCarrito] = useState<ItemVenta[]>([]);
  const [modalCobro, setModalCobro] = useState(false);
  const [metodoPago, setMetodoPago] = useState<MetodoPago>("EFECTIVO");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [avisoEscaneo, setAvisoEscaneo] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  // HU-C03: desplegable de autocompletado del buscador
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false);
  const [indiceSugerencia, setIndiceSugerencia] = useState(0);
  const inputBusqueda = useRef<HTMLInputElement>(null);

  // El escáner "tipea" donde esté el cursor: si el foco quedó en el body (tras un
  // clic en cualquier parte), lo devolvemos al buscador para no perder el escaneo.
  useEffect(() => {
    function recuperarFoco(e: KeyboardEvent) {
      const objetivo = e.target as HTMLElement;
      const enCampo = ["INPUT", "TEXTAREA", "SELECT"].includes(objetivo.tagName);
      if (!enCampo && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        inputBusqueda.current?.focus();
      }
    }
    window.addEventListener("keydown", recuperarFoco);
    return () => window.removeEventListener("keydown", recuperarFoco);
  }, []);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    const activos = productos.filter((p) => p.activo && p.stock > 0);
    if (!q) return activos;
    return activos.filter((p) => p.nombre.toLowerCase().includes(q) || p.codigo.includes(q));
  }, [productos, busqueda]);

  const total = carrito.reduce((suma, i) => suma + i.precio_unitario * i.cantidad, 0);

  // HU-C03: mientras se escribe, el sistema sugiere en un desplegable los
  // productos que coinciden por nombre o código (máx. 8, navegable con flechas).
  const sugerencias = useMemo(
    () => (busqueda.trim() ? visibles.slice(0, 8) : []),
    [busqueda, visibles]
  );

  function agregarYLimpiar(p: Producto) {
    agregar(p);
    setAvisoEscaneo(null);
    setBusqueda("");
    setMostrarSugerencias(false);
    setIndiceSugerencia(0);
    inputBusqueda.current?.focus();
  }

  // Enter en el buscador = fin de un escaneo (o búsqueda manual): si el texto
  // coincide exacto con un código, ese producto entra al carrito al instante;
  // si no, entra la sugerencia seleccionada del desplegable.
  function manejarEnterBusqueda() {
    const texto = busqueda.trim();
    if (!texto) return;
    const porCodigo = productos.find((p) => p.codigo === texto);
    if (porCodigo) {
      if (!porCodigo.activo || porCodigo.stock <= 0) {
        setAvisoEscaneo(`'${porCodigo.nombre}' no tiene stock disponible.`);
        setBusqueda("");
        return;
      }
      agregarYLimpiar(porCodigo);
      return;
    }
    if (sugerencias.length > 0) {
      agregarYLimpiar(sugerencias[Math.min(indiceSugerencia, sugerencias.length - 1)]);
      return;
    }
    setAvisoEscaneo(`No hay ningún producto que coincida con "${texto}".`);
  }

  function manejarTeclasBusqueda(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      manejarEnterBusqueda();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setIndiceSugerencia((i) => Math.min(i + 1, sugerencias.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setIndiceSugerencia((i) => Math.max(i - 1, 0));
    } else if (e.key === "Escape") {
      setMostrarSugerencias(false);
    }
  }

  function stockDe(productoId: number): number {
    return productos.find((p) => p.id === productoId)?.stock ?? 0;
  }

  function agregar(p: Producto) {
    setCarrito((actual) => {
      const existente = actual.find((i) => i.producto_id === p.id);
      if (existente) {
        return actual.map((i) =>
          i.producto_id === p.id ? { ...i, cantidad: Math.min(i.cantidad + 1, p.stock) } : i
        );
      }
      return [...actual, { producto_id: p.id, nombre: p.nombre, precio_unitario: p.precio, cantidad: 1 }];
    });
  }

  function cambiarCantidad(productoId: number, delta: number) {
    setCarrito((actual) =>
      actual
        .map((i) =>
          i.producto_id === productoId
            ? { ...i, cantidad: Math.min(Math.max(i.cantidad + delta, 0), stockDe(productoId)) }
            : i
        )
        .filter((i) => i.cantidad > 0)
    );
  }

  // HU-C02: escribir la cantidad directamente (ej. 5 botellas) sin escanear 5 veces.
  // Mientras se edita puede quedar en 0 (campo vacío); al salir del campo se normaliza.
  function fijarCantidad(productoId: number, cantidad: number) {
    const limpia = Number.isNaN(cantidad) ? 0 : Math.min(Math.max(cantidad, 0), stockDe(productoId));
    setCarrito((actual) =>
      actual.map((i) => (i.producto_id === productoId ? { ...i, cantidad: limpia } : i))
    );
  }

  function normalizarCantidad(productoId: number) {
    setCarrito((actual) => actual.filter((i) => i.producto_id !== productoId || i.cantidad > 0));
  }

  async function manejarCobrar() {
    setProcesando(true);
    setErrorAccion(null);
    try {
      const venta = await registrar({
        items: carrito.map((i) => ({ producto_id: i.producto_id, cantidad: i.cantidad })),
        metodo_pago: metodoPago,
      });
      setMensaje(`Venta #${venta.id} registrada: S/ ${venta.total.toFixed(2)} (${venta.metodo_pago}).`);
      setCarrito([]);
      setModalCobro(false);
      void recargarProductos(); // refleja el stock ya descontado
      inputBusqueda.current?.focus();
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (noDisponible || cajaNoDisponible) {
    return (
      <div>
        <PageHeader titulo="Punto de venta" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas (Módulo C)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando productos…" />;

  return (
    <div>
      <PageHeader
        titulo="Punto de venta"
        acciones={
          turno?.estado === "ABIERTO" ? (
            <Badge tono="exito">Caja abierta</Badge>
          ) : (
            <Badge tono="alerta">Caja cerrada: abre un turno para vender</Badge>
          )
        }
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        {/* Productos: botones grandes para tocar */}
        <div>
          <div className="relative mb-3">
            <ScanBarcode className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" aria-hidden />
            <Input
              ref={inputBusqueda}
              className="pl-9"
              autoFocus
              placeholder="Escanea un código o busca por nombre…"
              value={busqueda}
              onChange={(e) => {
                setBusqueda(e.target.value);
                setAvisoEscaneo(null);
                setMostrarSugerencias(true);
                setIndiceSugerencia(0);
              }}
              onKeyDown={manejarTeclasBusqueda}
              onFocus={() => setMostrarSugerencias(true)}
              onBlur={() => setTimeout(() => setMostrarSugerencias(false), 150)}
              role="combobox"
              aria-expanded={mostrarSugerencias && sugerencias.length > 0}
              aria-autocomplete="list"
            />
            {/* HU-C03: desplegable de autocompletado (nombre o código) */}
            {mostrarSugerencias && sugerencias.length > 0 && (
              <ul
                role="listbox"
                className="absolute z-30 mt-1 w-full overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-lg"
              >
                {sugerencias.map((p, indice) => (
                  <li key={p.id} role="option" aria-selected={indice === indiceSugerencia}>
                    <button
                      type="button"
                      // onMouseDown para ganarle al onBlur del input
                      onMouseDown={(e) => {
                        e.preventDefault();
                        agregarYLimpiar(p);
                      }}
                      onMouseEnter={() => setIndiceSugerencia(indice)}
                      className={`flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm ${
                        indice === indiceSugerencia ? "bg-zinc-100" : ""
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-zinc-800">{p.nombre}</span>
                        <span className="font-mono text-xs text-zinc-400">{p.codigo}</span>
                      </span>
                      <span className="shrink-0 text-right">
                        <span className="block font-semibold tabular-nums text-zinc-900">
                          S/ {p.precio.toFixed(2)}
                        </span>
                        <span className="text-xs text-zinc-400">stock: {p.stock}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {avisoEscaneo && (
            <div className="mb-3">
              <Alert tono="alerta">{avisoEscaneo}</Alert>
            </div>
          )}
          {visibles.length === 0 ? (
            <Card sinPadding>
              <EmptyState
                icono={Search}
                titulo="Sin resultados"
                descripcion="Ningún producto activo con stock coincide."
              />
            </Card>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
              {visibles.map((p) => (
                <button
                  key={p.id}
                  onClick={() => agregar(p)}
                  className="min-h-tactil rounded-xl border border-zinc-200 bg-white p-3 text-left shadow-tarjeta transition-colors hover:border-zinc-400 active:bg-zinc-50"
                >
                  <p className="line-clamp-2 text-sm font-medium text-zinc-800">{p.nombre}</p>
                  <p className="mt-1 text-sm font-semibold tabular-nums text-zinc-900">
                    S/ {p.precio.toFixed(2)}
                  </p>
                  <p className="text-xs text-zinc-400">stock: {p.stock}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Carrito */}
        <Card titulo="Venta actual" sinPadding className="h-fit lg:sticky lg:top-16">
          {carrito.length === 0 ? (
            <EmptyState icono={ShoppingCart} titulo="Carrito vacío" descripcion="Toca un producto para agregarlo." />
          ) : (
            <div>
              <ul className="divide-y divide-zinc-100 px-4">
                {carrito.map((item) => (
                  <li key={item.producto_id} className="flex items-center gap-2 py-2.5">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-zinc-800">{item.nombre}</p>
                      <p className="text-xs tabular-nums text-zinc-500">
                        S/ {item.precio_unitario.toFixed(2)} c/u
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variante="secundario"
                        compacto
                        aria-label={`Quitar uno de ${item.nombre}`}
                        onClick={() => cambiarCantidad(item.producto_id, -1)}
                        icono={<Minus className="h-4 w-4" aria-hidden />}
                      />
                      {/* HU-C02: la cantidad se escribe directo (ej. 5 botellas) */}
                      <input
                        type="number"
                        min={0}
                        max={stockDe(item.producto_id)}
                        inputMode="numeric"
                        aria-label={`Cantidad de ${item.nombre}`}
                        className="w-14 rounded-lg border border-zinc-300 px-1 py-1 text-center text-sm font-medium tabular-nums focus:border-zinc-500"
                        value={item.cantidad === 0 ? "" : item.cantidad}
                        onChange={(e) => fijarCantidad(item.producto_id, e.target.valueAsNumber)}
                        onBlur={() => normalizarCantidad(item.producto_id)}
                      />
                      <Button
                        variante="secundario"
                        compacto
                        aria-label={`Agregar uno de ${item.nombre}`}
                        onClick={() => cambiarCantidad(item.producto_id, 1)}
                        icono={<Plus className="h-4 w-4" aria-hidden />}
                      />
                    </div>
                    <span className="w-16 text-right text-sm font-medium tabular-nums">
                      S/ {(item.precio_unitario * item.cantidad).toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="space-y-3 border-t border-zinc-100 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-500">Total</span>
                  <span className="text-2xl font-semibold tabular-nums text-zinc-900">
                    S/ {total.toFixed(2)}
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variante="secundario"
                    onClick={() => setCarrito([])}
                    icono={<Trash2 className="h-4 w-4" aria-hidden />}
                  >
                    Vaciar
                  </Button>
                  <Button
                    className="flex-1"
                    disabled={turno?.estado !== "ABIERTO" || carrito.some((i) => i.cantidad <= 0)}
                    onClick={() => setModalCobro(true)}
                  >
                    Cobrar
                  </Button>
                </div>
                {turno?.estado !== "ABIERTO" && (
                  <p className="text-xs text-zinc-500">Abre la caja para poder cobrar.</p>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Confirmación de cobro */}
      <Modal
        abierto={modalCobro}
        titulo={`Cobrar S/ ${total.toFixed(2)}`}
        alCerrar={() => setModalCobro(false)}
        pie={
          <>
            <Button variante="secundario" onClick={() => setModalCobro(false)}>
              Cancelar
            </Button>
            <Button cargando={procesando} onClick={() => void manejarCobrar()}>
              Confirmar venta
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Select
            label="Método de pago"
            value={metodoPago}
            onChange={(e) => setMetodoPago(e.target.value as MetodoPago)}
          >
            {METODOS_PAGO.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </Select>
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
        </div>
      </Modal>
    </div>
  );
}
