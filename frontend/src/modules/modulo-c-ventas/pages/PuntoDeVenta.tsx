// Página del punto de venta (POS): registrar una venta Y consultar el catálogo.
// La tabla de la izquierda es la vista de solo lectura de todo lo disponible
// (código, nombre, categoría, precio, stock y estado); el carrito va a la derecha.
// El catálogo viene del módulo B (puerto de productos).
//
// Cómo se carga un producto a la venta:
//   1. escaneándolo (el lector escribe en el buscador y termina con Enter), o
//   2. haciendo clic/tap en su fila de la tabla.
//
// Escáner (HU-C01): el lector de barras/QR emula un teclado y termina con Enter.
// El buscador mantiene el foco (se recupera solo si se pierde). Al recibir Enter
// SOLO agrega si el código COMPLETO coincide exacto (nunca el primer producto
// parecido); si no calza, reintenta con el código invertido por si el lector lo
// leyó al revés, y si aun así no existe muestra un aviso sin agregar nada.
//
// Modo offline (HU-C10, RF-26): si se cae el internet el POS sigue vendiendo con
// el catálogo cacheado; las ventas quedan en el navegador y se sincronizan solas
// al volver la conexión (aviso visible del estado en la cabecera).
import { useEffect, useMemo, useRef, useState } from "react";
import {
  CloudUpload,
  Minus,
  Package,
  Plus,
  ScanBarcode,
  ShoppingCart,
  Trash2,
  Wifi,
  WifiOff,
} from "lucide-react";
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
} from "../../../shared/components/ui";
import { useAuthContext } from "../../../shared/lib/auth-context";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { PaginacionControles } from "../../modulo-b-inventario/components/PaginacionControles";
import { useCategorias } from "../../modulo-b-inventario/hooks/useCategorias";
import { useProductos } from "../../modulo-b-inventario/hooks/useProductos";
import { productosHttpAdapter } from "../../modulo-b-inventario/services/productos.http-adapter";
import type { FiltrosProductos, Producto } from "../../modulo-b-inventario/types";
import { ModalCobro } from "../components/ModalCobro";
import { ModalVentaRegistrada } from "../components/ModalVentaRegistrada";
import { useCaja } from "../hooks/useCaja";
import { useConexion } from "../hooks/useConexion";
import { useVenta } from "../hooks/useVenta";
import { cacheOffline, colaOffline } from "../services/ventas-offline";
import type { ItemVenta, NuevoPago, Venta } from "../types";

const DEBOUNCE_MS = 300;

/** Estado del producto según su stock (columna "Estado" de la tabla). */
function badgeDeStock(p: Producto) {
  if (p.stock <= 0) return <Badge tono="peligro">Sin stock</Badge>;
  if (p.stock_minimo > 0 && p.stock <= p.stock_minimo)
    return <Badge tono="alerta">Bajo stock</Badge>;
  return <Badge tono="exito">Disponible</Badge>;
}

/** Vuelto local para ventas offline: solo EFECTIVO reparte vuelto. */
function vueltoLocal(pagos: NuevoPago[], total: number): number {
  return pagos.reduce((suma, p) => {
    if (p.metodo !== "EFECTIVO" || p.monto_recibido === undefined) return suma;
    const monto = p.monto ?? total;
    return suma + Math.max(0, p.monto_recibido - monto);
  }, 0);
}

export default function PuntoDeVenta() {
  const { usuario } = useAuthContext();
  const { online } = useConexion();
  const {
    productos,
    paginados,
    cargando,
    noDisponible,
    recargar: recargarProductos,
  } = useProductos();
  const { categorias } = useCategorias();
  const { turno: turnoRemoto, noDisponible: cajaNoDisponible } = useCaja();
  const { registrar } = useVenta();

  // Catálogo efectivo: el del backend cuando hay conexión (y se cachea), el del
  // caché local cuando no la hay — así el POS nunca se queda sin productos.
  const [catalogo, setCatalogo] = useState<Producto[]>([]);
  useEffect(() => {
    if (productos.length > 0) {
      setCatalogo(productos);
      cacheOffline.guardarProductos(productos);
    } else if (!online) {
      setCatalogo(cacheOffline.productos());
    }
  }, [productos, online]);

  // Turno efectivo: igual que el catálogo (cacheado para operar sin backend).
  useEffect(() => {
    if (turnoRemoto !== null) cacheOffline.guardarTurno(turnoRemoto);
  }, [turnoRemoto]);
  const turno = turnoRemoto ?? (!online ? cacheOffline.turno() : null);

  // Cola de ventas pendientes de sincronizar.
  const [pendientes, setPendientes] = useState(() => colaOffline.listar().length);
  const [avisoSync, setAvisoSync] = useState<string | null>(null);
  const sincronizando = useRef(false);
  useEffect(() => {
    if (!online || colaOffline.listar().length === 0 || sincronizando.current) return;
    sincronizando.current = true;
    void colaOffline
      .sincronizar()
      .then(({ sincronizadas, conError }) => {
        setPendientes(colaOffline.listar().length);
        if (sincronizadas.length > 0) {
          setAvisoSync(
            `Volvió la conexión: se enviaron ${sincronizadas.length} venta(s) que habían quedado guardadas en este equipo.`
          );
          void recargarProductos();
        }
        if (conError.length > 0) {
          setAvisoSync(
            `Atención: ${conError.length} venta(s) guardada(s) en este equipo no se pudieron registrar ` +
              `(${conError[0].error ?? ""}). Revísalas con la administradora.`
          );
        }
      })
      .finally(() => {
        sincronizando.current = false;
      });
  }, [online, recargarProductos]);

  const [busqueda, setBusqueda] = useState("");
  // Filtros de la tabla-catálogo (se aplican en el servidor cuando hay conexión).
  const [filtroCategoria, setFiltroCategoria] = useState<number | "">("");
  const [filtroEstado, setFiltroEstado] = useState<"todos" | "disponible" | "bajo_minimo" | "sin_stock">("todos");
  const [precioMin, setPrecioMin] = useState("");
  const [precioMax, setPrecioMax] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [carrito, setCarrito] = useState<ItemVenta[]>(() => cacheOffline.carrito());
  const [modalCobro, setModalCobro] = useState(false);
  // HU-C05: venta recién cerrada, para ofrecer el ticket opcional y mostrar el vuelto
  const [ventaRegistrada, setVentaRegistrada] = useState<Venta | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [avisoEscaneo, setAvisoEscaneo] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  // Persistir el carrito en localStorage para conservar los productos al navegar entre módulos
  useEffect(() => {
    cacheOffline.guardarCarrito(carrito);
  }, [carrito]);

  // HU-C03: desplegable de autocompletado del buscador.
  // `indiceSugerencia === -1` = ninguna sugerencia resaltada: Enter se trata
  // como un escaneo (código exacto) y NO elige la primera opción del desplegable.
  // Solo al navegar con ↑/↓ (índice >= 0) Enter agrega la sugerencia resaltada.
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false);
  const [indiceSugerencia, setIndiceSugerencia] = useState(-1);
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

  // Los filtros viajan al backend (así no dependemos de cuántos productos haya).
  // Sin conexión se filtra sobre el caché local para poder seguir vendiendo.
  useEffect(() => {
    if (!online) return;
    const handle = window.setTimeout(() => {
      const filtros: FiltrosProductos = { page, page_size: pageSize, activo: true };
      if (busqueda.trim()) filtros.search = busqueda.trim();
      if (filtroCategoria !== "") filtros.categoria_id = filtroCategoria;
      if (filtroEstado === "disponible") filtros.solo_con_stock = true;
      if (filtroEstado === "bajo_minimo") filtros.solo_bajo_minimo = true;
      if (filtroEstado === "sin_stock") filtros.sin_stock = true;
      if (precioMin.trim()) filtros.precio_min = Number(precioMin);
      if (precioMax.trim()) filtros.precio_max = Number(precioMax);
      void recargarProductos(filtros);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busqueda, filtroCategoria, filtroEstado, precioMin, precioMax, page, pageSize, online]);

  const visibles = useMemo(() => {
    if (online) return catalogo;
    // Offline: mismos filtros, resueltos en memoria sobre el caché.
    const q = busqueda.trim().toLowerCase();
    return catalogo.filter((p) => {
      if (!p.activo) return false;
      if (q && !(p.nombre.toLowerCase().includes(q) || p.codigo.includes(q))) return false;
      if (filtroCategoria !== "" && p.categoria_id !== filtroCategoria) return false;
      if (filtroEstado === "disponible" && p.stock <= 0) return false;
      if (filtroEstado === "sin_stock" && p.stock > 0) return false;
      if (filtroEstado === "bajo_minimo" && !(p.stock_minimo > 0 && p.stock <= p.stock_minimo))
        return false;
      if (precioMin.trim() && p.precio < Number(precioMin)) return false;
      if (precioMax.trim() && p.precio > Number(precioMax)) return false;
      return true;
    });
  }, [online, catalogo, busqueda, filtroCategoria, filtroEstado, precioMin, precioMax]);

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
    setIndiceSugerencia(-1);
    inputBusqueda.current?.focus();
  }

  // Busca un producto cuyo código sea EXACTAMENTE `codigo` (nada de coincidencias
  // parciales). Primero en el catálogo cargado/cacheado —así funciona offline— y,
  // si hay conexión y no está en esta página, se lo pide al backend (búsqueda por
  // código, indexada y exacta), para no depender de los filtros ni la paginación.
  async function buscarPorCodigoExacto(codigo: string): Promise<Producto | null> {
    const local = catalogo.find((p) => p.codigo === codigo);
    if (local) return local;
    if (online) {
      try {
        const encontrado = await productosHttpAdapter.buscar(codigo);
        // Con ?codigo= el backend devuelve un único producto (match exacto).
        const producto = Array.isArray(encontrado) ? encontrado[0] : encontrado;
        // Defensa extra: exigir que el código devuelto sea idéntico al buscado.
        if (producto && producto.codigo === codigo) return producto;
      } catch {
        // 404 del backend: no existe ese código exacto.
      }
    }
    return null;
  }

  // Enter en el buscador = fin de un escaneo (o búsqueda manual). Reglas:
  //   1. Si el cajero resaltó una sugerencia con ↑/↓, esa manda (búsqueda por
  //      nombre con teclado).
  //   2. Si no, se trata como escaneo: SOLO agrega si el código COMPLETO coincide
  //      exacto. Ya no se cuela "el primer producto parecido" cuando el lector
  //      escribe el código a medias (o cuando se busca por nombre y se da Enter).
  //   3. Si no calza, reintenta con el código invertido: algunos lectores leen el
  //      código de barras al revés según el sentido del barrido.
  //   4. Si aun así no existe, avisa y NO agrega nada (limpia para el próximo
  //      escaneo).
  async function manejarEnterBusqueda() {
    const texto = busqueda.trim();
    if (!texto) return;

    // (1) Selección deliberada de una sugerencia con el teclado.
    if (indiceSugerencia >= 0 && sugerencias.length > 0) {
      agregarYLimpiar(sugerencias[Math.min(indiceSugerencia, sugerencias.length - 1)]);
      return;
    }

    // (2) Escaneo: código completo exacto.
    const exacto = await buscarPorCodigoExacto(texto);
    if (exacto) {
      agregarSiHayStock(exacto);
      return;
    }

    // (3) Lector que leyó el código al revés: reintento con el texto invertido,
    // también exacto. (Se omite si es capicúa: invertido == original.)
    const invertido = texto.split("").reverse().join("");
    if (invertido !== texto) {
      const alReves = await buscarPorCodigoExacto(invertido);
      if (alReves) {
        agregarSiHayStock(alReves);
        return;
      }
    }

    // (4) Nada coincide exacto: aviso sin agregar y campo limpio para reintentar.
    setAvisoEscaneo(
      `No se encontró un producto con el código "${texto}". Revisa que el lector ` +
        `haya leído el código completo, o toca el producto en la lista.`
    );
    setBusqueda("");
    setMostrarSugerencias(false);
    setIndiceSugerencia(-1);
  }

  /** Agrega al carrito si el producto está activo y tiene stock. */
  function agregarSiHayStock(p: Producto) {
    if (!p.activo || p.stock <= 0) {
      setAvisoEscaneo(`'${p.nombre}' no tiene stock disponible.`);
      setBusqueda("");
      return;
    }
    agregarYLimpiar(p);
  }

  function manejarTeclasBusqueda(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      void manejarEnterBusqueda();
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
    return catalogo.find((p) => p.id === productoId)?.stock ?? 0;
  }

  function agregar(p: Producto) {
    setCarrito((actual) => {
      const existente = actual.find((i) => i.producto_id === p.id);
      if (existente) {
        return actual.map((i) =>
          i.producto_id === p.id ? { ...i, cantidad: Math.min(i.cantidad + 1, p.stock) } : i
        );
      }
      return [...actual, { producto_id: p.id, nombre: p.nombre, precio_unitario: p.precio, cantidad: 1, stock: p.stock }];
    });
  }

  function cambiarCantidad(productoId: number, delta: number) {
    setCarrito((actual) =>
      actual
        .map((i) =>
          i.producto_id === productoId
            ? { ...i, cantidad: Math.min(Math.max(i.cantidad + delta, 0), i.stock ?? stockDe(productoId)) }
            : i
        )
        .filter((i) => i.cantidad > 0)
    );
  }

  // HU-C02: escribir la cantidad directamente (ej. 5 botellas) sin escanear 5 veces.
  // Mientras se edita puede quedar en 0 (campo vacío); al salir del campo se normaliza.
  function fijarCantidad(productoId: number, cantidad: number) {
    setCarrito((actual) => {
      const item = actual.find((i) => i.producto_id === productoId);
      const maxStock = item?.stock ?? stockDe(productoId);
      const limpia = Number.isNaN(cantidad) ? 0 : Math.min(Math.max(cantidad, 0), maxStock);
      return actual.map((i) => (i.producto_id === productoId ? { ...i, cantidad: limpia } : i));
    });
  }

  function normalizarCantidad(productoId: number) {
    setCarrito((actual) => actual.filter((i) => i.producto_id !== productoId || i.cantidad > 0));
  }

  function armarItemsVenta(): { producto_id: number; cantidad: number }[] {
    return carrito.map((i) => ({ producto_id: i.producto_id, cantidad: i.cantidad }));
  }

  // Venta sin conexión: se guarda local con uuid y se descuenta el stock del
  // caché para no sobrevender. Se sincroniza sola al volver el internet.
  function cobrarOffline(pagos: NuevoPago[]) {
    const totalVenta = total;
    const resumenMetodo = pagos.length === 1 ? pagos[0].metodo : "MIXTO";
    const vuelto = vueltoLocal(pagos, totalVenta);
    const pendiente = colaOffline.guardar(
      { items: armarItemsVenta(), pagos },
      { items: carrito, total: totalVenta, metodo_pago: resumenMetodo, vuelto }
    );
    setCatalogo(cacheOffline.descontarStock(pendiente.venta.items));
    setPendientes(colaOffline.listar().length);
    setCarrito([]);
    setModalCobro(false);
    setMensaje(null);
    // Pseudo-venta (id 0) para el modal de vuelto y el ticket opcional.
    setVentaRegistrada({
      id: 0,
      items: carrito,
      total: totalVenta,
      metodo_pago: resumenMetodo,
      pagos: [],
      vuelto,
      vendedor: usuario?.nombre ?? "",
      anulada: false,
      estado: "COMPLETADA",
      turno_id: turno?.id ?? 0,
      created_at: pendiente.vendida_en,
    });
  }

  async function manejarCobrar(pagos: NuevoPago[]) {
    if (!online) {
      cobrarOffline(pagos);
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      const venta = await registrar({
        items: armarItemsVenta(),
        pagos,
      });
      const conVuelto = venta.vuelto > 0 ? ` · Vuelto: S/ ${venta.vuelto.toFixed(2)}` : "";
      setMensaje(
        `Venta #${venta.id} registrada: S/ ${venta.total.toFixed(2)} (${venta.metodo_pago})${conVuelto}.`
      );
      setCarrito([]);
      setModalCobro(false);
      setVentaRegistrada(venta); // abre el modal con vuelto + ticket opcional
      void recargarProductos(); // refleja el stock ya descontado
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  // Sin conexión se sigue vendiendo con el caché; la pantalla "no conectado"
  // solo aparece si estando EN LÍNEA el backend aún no expone los endpoints.
  if ((noDisponible || cajaNoDisponible) && online) {
    return (
      <div>
        <PageHeader titulo="Punto de venta" />
        <Card sinPadding>
          <ModuloPendiente modulo="ventas" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando productos…" />;

  // Catálogo de consulta: código, nombre, categoría, precio, stock y estado.
  const columnasCatalogo: Columna<Producto>[] = [
    {
      titulo: "Código",
      ancho: "110px",
      render: (p) => <span className="font-mono text-xs text-zinc-500 truncate block">{p.codigo}</span>,
    },
    {
      titulo: "Producto",
      ancho: "170px",
      render: (p) => <span className="font-medium text-zinc-800 leading-snug line-clamp-2">{p.nombre}</span>,
    },
    {
      titulo: "Categoría",
      ancho: "120px",
      soloEscritorio: true,
      render: (p) => <span className="text-zinc-600 truncate block">{p.categoria_nombre ?? "—"}</span>,
    },
    {
      titulo: "Precio",
      ancho: "85px",
      render: (p) => <span className="tabular-nums font-medium whitespace-nowrap">S/ {p.precio.toFixed(2)}</span>,
    },
    {
      titulo: "Stock",
      ancho: "60px",
      render: (p) => <span className="tabular-nums font-medium text-center block">{p.stock}</span>,
    },
    {
      titulo: "Estado",
      ancho: "105px",
      render: (p) => badgeDeStock(p),
    },
  ];

  return (
    // En escritorio la pantalla se reparte el alto disponible: la grilla se
    // queda con lo que sobra y cada columna scrollea por dentro (catálogo y
    // carrito). En móvil se apila y scrollea la página, como corresponde.
    <div className="lg:flex lg:h-full lg:min-h-0 lg:flex-col">
      <PageHeader
        titulo="Punto de venta"
        acciones={
          <div className="flex flex-wrap items-center gap-2">
            {/* HU-C10: aviso visible del estado de conexión */}
            {online ? (
              <Badge tono="exito">
                <Wifi className="h-3.5 w-3.5" aria-hidden /> En línea
              </Badge>
            ) : (
              <Badge tono="peligro">
                <WifiOff className="h-3.5 w-3.5" aria-hidden /> Sin conexión — modo local
              </Badge>
            )}
            {pendientes > 0 && (
              <Badge tono="alerta">
                <CloudUpload className="h-3.5 w-3.5" aria-hidden /> {pendientes} venta(s) por enviar
              </Badge>
            )}
            {turno?.estado === "ABIERTO" ? (
              <Badge tono="exito">Caja abierta</Badge>
            ) : (
              <Badge tono="alerta">Caja cerrada — Abre turno</Badge>
            )}
          </div>
        }
      />

      {avisoSync && (
        <div className="mb-4">
          <Alert tono={avisoSync.startsWith("Atención") ? "alerta" : "exito"}>{avisoSync}</Alert>
        </div>
      )}
      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}

      {/* `grid-rows-[minmax(0,1fr)]` no es decorativo: sin él la fila es `auto`,
          o sea del alto de su contenido, y como las grillas no recortan, el
          catálogo y el carrito se desbordaban de la grilla y estiraban la
          página igual. Además dejaba sin resolver el `max-h-full` del carrito,
          porque un porcentaje contra un alto automático no significa nada. */}
      <div className="grid w-full min-w-0 gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[1fr_20rem] lg:grid-rows-[minmax(0,1fr)]">
        {/* Productos: botones grandes para tocar */}
        <div className="w-full min-w-0 lg:flex lg:min-h-0 lg:flex-col">
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
                setIndiceSugerencia(-1);
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
                className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-zinc-200 bg-white p-1 shadow-2xl divide-y divide-zinc-50"
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
                      className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        indice === indiceSugerencia ? "bg-zinc-100 font-medium" : "hover:bg-zinc-50 text-zinc-700"
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

          {/* Filtros del catálogo: categoría, estado de stock y rango de precio.
              (la búsqueda por nombre/código es el mismo campo que usa el lector) */}
          <div className="mb-3 grid w-full min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <Select
              aria-label="Filtrar por categoría"
              value={filtroCategoria}
              onChange={(e) => {
                setFiltroCategoria(e.target.value ? Number(e.target.value) : "");
                setPage(1);
              }}
            >
              <option value="">Todas las categorías</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Filtrar por estado de stock"
              value={filtroEstado}
              onChange={(e) => {
                setFiltroEstado(e.target.value as typeof filtroEstado);
                setPage(1);
              }}
            >
              <option value="todos">Todo el stock</option>
              <option value="disponible">Disponible</option>
              <option value="bajo_minimo">Bajo mínimo</option>
              <option value="sin_stock">Sin stock</option>
            </Select>
            <Input
              type="number"
              min={0}
              step="0.01"
              placeholder="Precio desde"
              aria-label="Precio mínimo"
              value={precioMin}
              onChange={(e) => {
                setPrecioMin(e.target.value);
                setPage(1);
              }}
            />
            <Input
              type="number"
              min={0}
              step="0.01"
              placeholder="Precio hasta"
              aria-label="Precio máximo"
              value={precioMax}
              onChange={(e) => {
                setPrecioMax(e.target.value);
                setPage(1);
              }}
            />
          </div>

          {/* Catálogo en tabla (solo lectura). Un clic en la fila lo agrega a la venta. */}
          <Card
            sinPadding
            className="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col"
            cuerpoClassName="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col"
          >
            <Table
              minAncho="530px"
              altoDelContenedor
              // En móvil las columnas se apilan y el carrito queda debajo: sin
              // tope, el catálogo se despliega entero y hay que scrollear media
              // pantalla para llegar a Cobrar. De lg en adelante manda el flex.
              contenedorClassName="max-h-[50vh] lg:max-h-none lg:min-h-0 lg:flex-1"
              columnas={columnasCatalogo}
              filas={visibles}
              claveDe={(p) => p.id}
              alHacerClicFila={(p) => agregarSiHayStock(p)}
              vacio={
                <EmptyState
                  icono={Package}
                  titulo="Sin resultados"
                  descripcion="Ningún producto coincide con la búsqueda o los filtros."
                />
              }
            />
            {online && (
              <PaginacionControles
                paginados={paginados}
                page={page}
                pageSize={pageSize}
                onCambiarPage={setPage}
                onCambiarPageSize={(n) => {
                  setPageSize(n);
                  setPage(1);
                }}
                etiqueta="productos"
              />
            )}
          </Card>
        </div>

        {/* Carrito */}
        <Card
          titulo="Venta actual"
          sinPadding
          className="h-fit lg:flex lg:max-h-full lg:flex-col"
          cuerpoClassName="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col"
        >
          {carrito.length === 0 ? (
            <EmptyState icono={ShoppingCart} titulo="Carrito vacío" descripcion="Toca un producto para agregarlo." />
          ) : (
            <div className="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col">
              {/* La lista se queda con el alto que sobra y scrollea sola: si
                  creciera libre estiraría la página y volvería a aparecer la
                  barra vertical de la pantalla. El total y los botones de abajo
                  quedan siempre a la vista. */}
              <ul className="max-h-[45vh] divide-y divide-zinc-100 overflow-y-auto px-4 lg:max-h-none lg:min-h-0 lg:flex-1">
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
              <div className="shrink-0 space-y-3 border-t border-zinc-100 p-4">
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

      {/* Confirmación de cobro (HU-C04): método de pago, pago mixto y vuelto. */}
      <ModalCobro
        abierto={modalCobro}
        total={total}
        procesando={procesando}
        error={errorAccion}
        alCerrar={() => {
          setModalCobro(false);
          setErrorAccion(null);
        }}
        alConfirmar={(pagos) => void manejarCobrar(pagos)}
      />

      {/* Post-venta (HU-C05): vuelto en grande + ticket térmico opcional */}
      <ModalVentaRegistrada
        venta={ventaRegistrada}
        alCerrar={() => {
          setVentaRegistrada(null);
          inputBusqueda.current?.focus();
        }}
      />
    </div>
  );
}
