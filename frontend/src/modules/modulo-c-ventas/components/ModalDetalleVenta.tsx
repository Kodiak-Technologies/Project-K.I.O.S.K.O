import { useEffect, useMemo, useState } from "react";
import { ArrowLeftRight, ListChecks, Minus, Plus, Search, Trash2, Undo2 } from "lucide-react";
import { Alert, Badge, Button, Input, Modal } from "../../../shared/components/ui";
import { productosHttpAdapter } from "../../modulo-b-inventario/services/productos.http-adapter";
import type { Producto } from "../../modulo-b-inventario/types";
import { useMetodosPago } from "../hooks/useMetodosPago";
import type { Venta } from "../types";

export type ModoGestion = "detalle" | "devolver" | "cambiar";

interface Props {
  venta: Venta | null;
  modoInicial?: ModoGestion;
  procesando: boolean;
  error: string | null;
  alCerrar: () => void;
  alDevolver: (items: { detalle_id: number; cantidad: number }[], motivo: string) => void;
  alCambiar: (payload: {
    devolver: { detalle_id: number; cantidad: number }[];
    nuevos: { producto_id: number; cantidad: number }[];
    metodo: string;
    motivo: string;
  }) => void;
}

interface Reemplazo {
  producto: Producto;
  cantidad: number;
}

export function ModalDetalleVenta({
  venta,
  modoInicial = "detalle",
  procesando,
  error,
  alCerrar,
  alDevolver,
  alCambiar,
}: Props) {
  const { metodos } = useMetodosPago();
  const [modo, setModo] = useState<ModoGestion>(modoInicial);
  const [cantidades, setCantidades] = useState<Record<number, string>>({});
  const [motivo, setMotivo] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<Producto[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [reemplazos, setReemplazos] = useState<Reemplazo[]>([]);
  const [metodo, setMetodo] = useState("EFECTIVO");

  useEffect(() => {
    setModo(modoInicial);
    setCantidades({});
    setMotivo("");
    setBusqueda("");
    setResultados([]);
    setReemplazos([]);
  }, [venta?.id, modoInicial]);

  useEffect(() => {
    if (metodos.length > 0 && !metodos.some((m) => m.codigo === metodo)) {
      setMetodo(metodos.find((m) => m.codigo === "EFECTIVO")?.codigo ?? metodos[0].codigo);
    }
  }, [metodos, metodo]);

  useEffect(() => {
    if (modo !== "cambiar") return;
    const q = busqueda.trim();
    if (!q) {
      setResultados([]);
      return;
    }
    const handle = window.setTimeout(async () => {
      setBuscando(true);
      try {
        const resp = await productosHttpAdapter.listar({ search: q, page_size: 8, activo: true });
        setResultados(resp.items);
      } catch {
        setResultados([]);
      } finally {
        setBuscando(false);
      }
    }, 300);
    return () => window.clearTimeout(handle);
  }, [busqueda, modo]);

  const lineasDevolvibles = useMemo(() => {
    if (!venta) return [];
    return venta.items
      .filter((i) => i.id !== undefined)
      .map((i) => ({ ...i, restante: i.cantidad - (i.cantidad_devuelta ?? 0) }))
      .filter((i) => i.restante > 0);
  }, [venta]);

  if (!venta) return null;

  const puedeGestionar = !venta.anulada && lineasDevolvibles.length > 0;
  const modoEfectivo: ModoGestion = puedeGestionar ? modo : "detalle";

  const seleccionDev = lineasDevolvibles
    .map((l) => ({ detalle_id: l.id as number, cantidad: Number(cantidades[l.id as number]) || 0, linea: l }))
    .filter((s) => s.cantidad > 0);
  const montoDevuelto = seleccionDev.reduce((suma, s) => suma + s.cantidad * s.linea.precio_unitario, 0);
  const devVale =
    seleccionDev.length > 0 && seleccionDev.every((s) => s.cantidad <= s.linea.restante);

  const montoNuevo = reemplazos.reduce((suma, r) => suma + r.cantidad * r.producto.precio, 0);
  const diferencia = Math.round((montoNuevo - montoDevuelto) * 100) / 100;
  const reemplazosValidos =
    reemplazos.length > 0 && reemplazos.every((r) => r.cantidad > 0 && r.cantidad <= r.producto.stock);

  const validDevolver = devVale && motivo.trim().length > 0;
  const validCambiar = devVale && reemplazosValidos && motivo.trim().length > 0 && metodo !== "";

  function fijarCantidad(detalleId: number, valor: string) {
    setCantidades((actual) => ({ ...actual, [detalleId]: valor }));
  }

  function agregarReemplazo(p: Producto) {
    setReemplazos((actual) => {
      const existe = actual.find((r) => r.producto.id === p.id);
      if (existe) {
        return actual.map((r) =>
          r.producto.id === p.id ? { ...r, cantidad: Math.min(r.cantidad + 1, p.stock) } : r
        );
      }
      return [...actual, { producto: p, cantidad: 1 }];
    });
    setBusqueda("");
    setResultados([]);
  }

  function cambiarCantReemplazo(id: number, delta: number) {
    setReemplazos((actual) =>
      actual
        .map((r) =>
          r.producto.id === id
            ? { ...r, cantidad: Math.min(Math.max(r.cantidad + delta, 0), r.producto.stock) }
            : r
        )
        .filter((r) => r.cantidad > 0)
    );
  }

  function quitarReemplazo(id: number) {
    setReemplazos((actual) => actual.filter((r) => r.producto.id !== id));
  }

  function confirmar() {
    if (modoEfectivo === "devolver") {
      alDevolver(
        seleccionDev.map(({ detalle_id, cantidad }) => ({ detalle_id, cantidad })),
        motivo.trim()
      );
    } else if (modoEfectivo === "cambiar") {
      alCambiar({
        devolver: seleccionDev.map(({ detalle_id, cantidad }) => ({ detalle_id, cantidad })),
        nuevos: reemplazos.map((r) => ({ producto_id: r.producto.id, cantidad: r.cantidad })),
        metodo,
        motivo: motivo.trim(),
      });
    }
  }

  const totalVendido = venta.items.reduce((s, i) => s + i.precio_unitario * i.cantidad, 0);

  const pie =
    modoEfectivo === "detalle" ? (
      <Button variante="secundario" onClick={alCerrar}>
        Cerrar
      </Button>
    ) : (
      <>
        <Button variante="secundario" onClick={alCerrar}>
          Cancelar
        </Button>
        {modoEfectivo === "devolver" ? (
          <Button variante="peligro" cargando={procesando} disabled={!validDevolver} onClick={confirmar}>
            Registrar devolución
          </Button>
        ) : (
          <Button cargando={procesando} disabled={!validCambiar} onClick={confirmar}>
            Registrar cambio
          </Button>
        )}
      </>
    );

  return (
    <Modal abierto={venta !== null} titulo={`Venta #${venta.id}`} alCerrar={alCerrar} pie={pie}>
      <div className="space-y-4">
        {/* Resumen de la venta */}
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-zinc-50 px-3 py-2.5 text-sm">
          <div className="text-zinc-600">
            <span className="text-zinc-500">{venta.created_at ? new Date(venta.created_at).toLocaleString("es-PE") : "—"}</span>
            {venta.vendedor && <span className="text-zinc-400"> · {venta.vendedor}</span>}
          </div>
          <div className="flex items-center gap-2">
            {venta.estado === "ANULADA" ? (
              <Badge tono="peligro">Anulada</Badge>
            ) : venta.estado === "DEVUELTA_PARCIAL" ? (
              <Badge tono="alerta">Dev. parcial</Badge>
            ) : (
              <Badge tono="exito">Válida</Badge>
            )}
            <span className="font-semibold tabular-nums text-zinc-900">S/ {venta.total.toFixed(2)}</span>
          </div>
        </div>

        {/* Pestañas: solo cuando la venta admite reversos */}
        {puedeGestionar && (
          <div className="flex rounded-lg border border-zinc-200 p-0.5 text-sm">
            {([
              ["detalle", "Detalle", ListChecks],
              ["devolver", "Devolver", Undo2],
              ["cambiar", "Cambiar", ArrowLeftRight],
            ] as const).map(([valor, etiqueta, Icono]) => (
              <button
                key={valor}
                type="button"
                onClick={() => setModo(valor)}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 font-medium transition-colors ${
                  modoEfectivo === valor ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-50"
                }`}
              >
                <Icono className="h-4 w-4" aria-hidden /> {etiqueta}
              </button>
            ))}
          </div>
        )}

        {/* ---------- DETALLE (solo lectura) ---------- */}
        {modoEfectivo === "detalle" && (
          <ul className="divide-y divide-zinc-100">
            {venta.items.map((item, idx) => (
              <li key={item.id ?? idx} className="flex items-start justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="text-sm text-zinc-800">
                    <span className="font-medium tabular-nums">{item.cantidad}×</span> {item.nombre}
                  </p>
                  <p className="text-xs text-zinc-500">
                    S/ {item.precio_unitario.toFixed(2)} c/u
                    {(item.cantidad_devuelta ?? 0) > 0 && (
                      <span className="text-alerta"> · devueltas: {item.cantidad_devuelta}</span>
                    )}
                  </p>
                </div>
                <span className="shrink-0 text-sm font-medium tabular-nums text-zinc-900">
                  S/ {(item.precio_unitario * item.cantidad).toFixed(2)}
                </span>
              </li>
            ))}
            <li className="flex items-center justify-between py-2.5 text-sm">
              <span className="text-zinc-500">Total</span>
              <span className="font-semibold tabular-nums text-zinc-900">S/ {totalVendido.toFixed(2)}</span>
            </li>
          </ul>
        )}

        {/* ---------- DEVOLVER ---------- */}
        {modoEfectivo === "devolver" && (
          <>
            <p className="text-sm text-zinc-600">
              Indica cuántas unidades vuelven de cada producto. El stock se repone y el dinero sale de la
              caja actual; todo queda registrado para la administradora.
            </p>
            <ul className="divide-y divide-zinc-100">
              {lineasDevolvibles.map((linea) => (
                <li key={linea.id} className="flex items-center gap-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-zinc-800">{linea.nombre}</p>
                    <p className="text-xs text-zinc-500">
                      vendidas: {linea.cantidad}
                      {(linea.cantidad_devuelta ?? 0) > 0 && ` · ya devueltas: ${linea.cantidad_devuelta}`}
                      {" · "}S/ {linea.precio_unitario.toFixed(2)} c/u
                    </p>
                  </div>
                  <input
                    type="number"
                    min={0}
                    max={linea.restante}
                    inputMode="numeric"
                    aria-label={`Unidades a devolver de ${linea.nombre}`}
                    placeholder="0"
                    className="w-16 rounded-lg border border-zinc-300 px-2 py-1.5 text-center text-sm tabular-nums focus:border-zinc-500"
                    value={cantidades[linea.id as number] ?? ""}
                    onChange={(e) => fijarCantidad(linea.id as number, e.target.value)}
                  />
                </li>
              ))}
            </ul>
            {montoDevuelto > 0 && (
              <div className="flex items-center justify-between rounded-lg bg-zinc-50 px-3 py-2.5 text-sm">
                <span className="text-zinc-600">A devolver al cliente</span>
                <span className="font-semibold tabular-nums">S/ {montoDevuelto.toFixed(2)}</span>
              </div>
            )}
            <Input
              label="Motivo"
              requerido
              placeholder="ej. producto vencido, cliente cambió de opinión…"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </>
        )}

        {/* ---------- CAMBIAR ---------- */}
        {modoEfectivo === "cambiar" && (
          <>
            {/* 1. Qué se devuelve */}
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-zinc-400">
                1 · Producto que devuelve
              </p>
              <ul className="divide-y divide-zinc-100">
                {lineasDevolvibles.map((linea) => (
                  <li key={linea.id} className="flex items-center gap-3 py-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-zinc-800">{linea.nombre}</p>
                      <p className="text-xs text-zinc-500">
                        quedan {linea.restante} · S/ {linea.precio_unitario.toFixed(2)} c/u
                      </p>
                    </div>
                    <input
                      type="number"
                      min={0}
                      max={linea.restante}
                      inputMode="numeric"
                      aria-label={`Unidades a devolver de ${linea.nombre}`}
                      placeholder="0"
                      className="w-16 rounded-lg border border-zinc-300 px-2 py-1.5 text-center text-sm tabular-nums focus:border-zinc-500"
                      value={cantidades[linea.id as number] ?? ""}
                      onChange={(e) => fijarCantidad(linea.id as number, e.target.value)}
                    />
                  </li>
                ))}
              </ul>
            </div>

            {/* 2. Producto de reemplazo (buscador del catálogo) */}
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-zinc-400">
                2 · Producto de reemplazo
              </p>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" aria-hidden />
                <Input
                  className="pl-9"
                  placeholder="Busca por nombre o código…"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                />
                {busqueda.trim() && (resultados.length > 0 || buscando) && (
                  <ul className="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-xl border border-zinc-200 bg-white shadow-lg">
                    {buscando && <li className="px-3 py-2.5 text-sm text-zinc-400">Buscando…</li>}
                    {!buscando &&
                      resultados.map((p) => {
                        const sinStock = p.stock <= 0;
                        return (
                          <li key={p.id}>
                            <button
                              type="button"
                              disabled={sinStock}
                              onClick={() => agregarReemplazo(p)}
                              className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              <span className="min-w-0">
                                <span className="block truncate font-medium text-zinc-800">{p.nombre}</span>
                                <span className="font-mono text-xs text-zinc-400">{p.codigo}</span>
                              </span>
                              <span className="shrink-0 text-right">
                                <span className="block font-semibold tabular-nums text-zinc-900">
                                  S/ {p.precio.toFixed(2)}
                                </span>
                                <span className="text-xs text-zinc-400">{sinStock ? "sin stock" : `stock: ${p.stock}`}</span>
                              </span>
                            </button>
                          </li>
                        );
                      })}
                  </ul>
                )}
              </div>

              {reemplazos.length > 0 && (
                <ul className="mt-2 divide-y divide-zinc-100">
                  {reemplazos.map((r) => (
                    <li key={r.producto.id} className="flex items-center gap-2 py-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-zinc-800">{r.producto.nombre}</p>
                        <p className="text-xs tabular-nums text-zinc-500">S/ {r.producto.precio.toFixed(2)} c/u</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variante="secundario"
                          compacto
                          aria-label={`Quitar uno de ${r.producto.nombre}`}
                          onClick={() => cambiarCantReemplazo(r.producto.id, -1)}
                          icono={<Minus className="h-4 w-4" aria-hidden />}
                        />
                        <span className="w-8 text-center text-sm font-medium tabular-nums">{r.cantidad}</span>
                        <Button
                          variante="secundario"
                          compacto
                          disabled={r.cantidad >= r.producto.stock}
                          aria-label={`Agregar uno de ${r.producto.nombre}`}
                          onClick={() => cambiarCantReemplazo(r.producto.id, 1)}
                          icono={<Plus className="h-4 w-4" aria-hidden />}
                        />
                        <Button
                          variante="fantasma"
                          compacto
                          aria-label={`Quitar ${r.producto.nombre}`}
                          onClick={() => quitarReemplazo(r.producto.id)}
                          icono={<Trash2 className="h-4 w-4 text-peligro" aria-hidden />}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Recálculo del monto: qué se cobra o qué se devuelve */}
            {(montoDevuelto > 0 || montoNuevo > 0) && (
              <div className="space-y-1 rounded-lg bg-zinc-50 px-3 py-2.5 text-sm">
                <div className="flex items-center justify-between text-zinc-600">
                  <span>Devuelve</span>
                  <span className="tabular-nums">S/ {montoDevuelto.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between text-zinc-600">
                  <span>Reemplazo</span>
                  <span className="tabular-nums">S/ {montoNuevo.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between border-t border-zinc-200 pt-1 font-semibold text-zinc-900">
                  <span>
                    {diferencia > 0 ? "El cliente paga" : diferencia < 0 ? "A favor del cliente" : "Sin diferencia"}
                  </span>
                  <span className="tabular-nums">S/ {Math.abs(diferencia).toFixed(2)}</span>
                </div>
              </div>
            )}

            {/* Método de pago del reemplazo (la venta nueva se registra con este método) */}
            {metodos.length > 0 && (
              <div>
                <p className="mb-1.5 text-sm font-medium text-zinc-700">Método de pago del reemplazo</p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {metodos.map((m) => (
                    <button
                      key={m.codigo}
                      type="button"
                      onClick={() => setMetodo(m.codigo)}
                      className={`rounded-xl border px-2 py-2 text-sm font-medium transition-colors ${
                        metodo === m.codigo
                          ? "border-zinc-900 bg-zinc-900 text-white"
                          : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400"
                      }`}
                    >
                      {m.nombre}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <Input
              label="Motivo del cambio"
              requerido
              placeholder="ej. cliente prefirió otro producto"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </>
        )}

        {error && <Alert tono="peligro">{error}</Alert>}
      </div>
    </Modal>
  );
}
