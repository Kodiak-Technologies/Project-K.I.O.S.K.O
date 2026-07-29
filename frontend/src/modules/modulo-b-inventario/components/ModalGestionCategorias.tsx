import { useMemo, useState } from "react";
import { Pencil, Plus, Search, Tag, Trash2, X } from "lucide-react";
import { Alert, Button, Input, Modal } from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import type { Categoria } from "../types";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  categorias: Categoria[];
  cargando: boolean;
  onCrear: (datos: { nombre: string }) => Promise<Categoria>;
  onEditar: (id: number, datos: { nombre?: string }) => Promise<Categoria>;
  onEliminar: (id: number) => Promise<void>;
}

export function ModalGestionCategorias({
  abierto,
  alCerrar,
  categorias,
  cargando,
  onCrear,
  onEditar,
  onEliminar,
}: Props) {
  const [busqueda, setBusqueda] = useState("");
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [nombreEdit, setNombreEdit] = useState("");

  const [creandoNueva, setCreandoNueva] = useState(false);
  const [nuevoNombre, setNuevoNombre] = useState("");

  const [porEliminar, setPorEliminar] = useState<Categoria | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [errorModal, setErrorModal] = useState<string | null>(null);
  const [mensajeModal, setMensajeModal] = useState<string | null>(null);

  const categoriasFiltradas = useMemo(() => {
    if (!busqueda.trim()) return categorias;
    const q = busqueda.trim().toLowerCase();
    return categorias.filter((c) => c.nombre.toLowerCase().includes(q));
  }, [categorias, busqueda]);

  const empezarEditar = (cat: Categoria) => {
    setErrorModal(null);
    setMensajeModal(null);
    setEditandoId(cat.id);
    setNombreEdit(cat.nombre);
  };

  const cancelarEditar = () => {
    setEditandoId(null);
    setNombreEdit("");
  };

  const guardarEdicion = async (id: number) => {
    if (!nombreEdit.trim()) {
      setErrorModal("El nombre de la categoría no puede estar vacío.");
      return;
    }
    setProcesando(true);
    setErrorModal(null);
    setMensajeModal(null);
    try {
      await onEditar(id, {
        nombre: nombreEdit.trim(),
      });
      setMensajeModal("Categoría actualizada correctamente.");
      setEditandoId(null);
    } catch (e) {
      setErrorModal(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  };

  const guardarNueva = async () => {
    if (!nuevoNombre.trim()) {
      setErrorModal("Ingresa un nombre para la categoría.");
      return;
    }
    setProcesando(true);
    setErrorModal(null);
    setMensajeModal(null);
    try {
      await onCrear({
        nombre: nuevoNombre.trim(),
      });
      setMensajeModal("Categoría creada correctamente.");
      setCreandoNueva(false);
      setNuevoNombre("");
    } catch (e) {
      setErrorModal(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  };

  const confirmarEliminar = async (id: number) => {
    setProcesando(true);
    setErrorModal(null);
    setMensajeModal(null);
    try {
      await onEliminar(id);
      setMensajeModal("Categoría eliminada correctamente.");
      setPorEliminar(null);
    } catch (e) {
      setErrorModal(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  };

  if (!abierto) return null;

  return (
    <Modal
      abierto={abierto}
      titulo="Gestión de Categorías"
      alCerrar={alCerrar}
      pie={
        <Button variante="secundario" onClick={alCerrar}>
          Cerrar
        </Button>
      }
    >
      <div className="space-y-4">
        {errorModal && <Alert tono="peligro">{errorModal}</Alert>}
        {mensajeModal && <Alert tono="exito">{mensajeModal}</Alert>}

        {/* Buscador + Crear Nueva */}
        <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar categoría por nombre..."
              className="w-full rounded-xl border border-zinc-200 bg-white py-2 pl-9 pr-8 text-sm focus:border-zinc-400 focus:outline-none placeholder:text-zinc-400"
            />
            {busqueda && (
              <button
                type="button"
                onClick={() => setBusqueda("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-zinc-400 hover:text-zinc-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          {!creandoNueva && (
            <Button
              variante="secundario"
              compacto
              onClick={() => {
                setCreandoNueva(true);
                setErrorModal(null);
              }}
              icono={<Plus className="h-4 w-4" />}
            >
              Agregar categoría
            </Button>
          )}
        </div>

        {/* Formulario de Alta Inline dentro del modal */}
        {creandoNueva && (
          <div className="rounded-xl border border-marca/30 bg-marca/5 p-3 space-y-2">
            <h4 className="text-xs font-semibold text-marca uppercase tracking-wider">Nueva Categoría</h4>
            <div className="flex flex-col sm:flex-row gap-2 items-center">
              <div className="flex-1 w-full">
                <Input
                  placeholder="ej. Bebidas"
                  value={nuevoNombre}
                  onChange={(e) => setNuevoNombre(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void guardarNueva();
                    }
                  }}
                  className="h-10 min-h-0"
                  autoFocus
                />
              </div>
              <div className="flex gap-2 shrink-0">
                <Button
                  variante="secundario"
                  onClick={() => {
                    setCreandoNueva(false);
                    setNuevoNombre("");
                  }}
                  disabled={procesando}
                  className="h-10 min-h-0"
                >
                  Cancelar
                </Button>
                <Button onClick={guardarNueva} cargando={procesando} className="h-10 min-h-0">
                  Guardar
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Alerta de confirmación de eliminación */}
        {porEliminar && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 space-y-2">
            <p className="text-sm font-medium text-red-900">
              ¿Seguro que deseas eliminar la categoría <strong>"{porEliminar.nombre}"</strong>?
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <Button
                variante="secundario"
                compacto
                onClick={() => setPorEliminar(null)}
                disabled={procesando}
              >
                Cancelar
              </Button>
              <Button
                variante="peligro"
                compacto
                onClick={() => void confirmarEliminar(porEliminar.id)}
                cargando={procesando}
              >
                Eliminar
              </Button>
            </div>
          </div>
        )}

        {/* Lista de categorías */}
        <div className="max-h-72 overflow-y-auto divide-y divide-zinc-100 rounded-xl border border-zinc-200 bg-white">
          {cargando ? (
            <div className="p-6 text-center text-sm text-zinc-500">Cargando categorías...</div>
          ) : categoriasFiltradas.length === 0 ? (
            <div className="p-6 text-center text-sm text-zinc-500">
              {busqueda ? "No se encontraron categorías coincidentes." : "No hay categorías registradas."}
            </div>
          ) : (
            categoriasFiltradas.map((cat) => {
              const estaEditando = editandoId === cat.id;

              if (estaEditando) {
                return (
                  <div key={cat.id} className="p-3 bg-zinc-50 flex flex-col sm:flex-row gap-2 items-center">
                    <div className="flex-1 w-full">
                      <Input
                        placeholder="Nombre de categoría"
                        value={nombreEdit}
                        onChange={(e) => setNombreEdit(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            void guardarEdicion(cat.id);
                          }
                          if (e.key === "Escape") cancelarEditar();
                        }}
                        className="h-10 min-h-0"
                        autoFocus
                      />
                    </div>
                    <div className="flex justify-end gap-2 shrink-0">
                      <Button
                        variante="secundario"
                        onClick={cancelarEditar}
                        disabled={procesando}
                        className="h-10 min-h-0"
                      >
                        Cancelar
                      </Button>
                      <Button
                        onClick={() => void guardarEdicion(cat.id)}
                        cargando={procesando}
                        className="h-10 min-h-0"
                      >
                        Guardar
                      </Button>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={cat.id}
                  className="flex items-center justify-between gap-3 p-3 hover:bg-zinc-50/80 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <Tag className="h-4 w-4 shrink-0 text-zinc-400" />
                    <span className="font-medium text-sm text-zinc-900 truncate">{cat.nombre}</span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => empezarEditar(cat)}
                      disabled={editandoId !== null || porEliminar !== null}
                      title="Editar categoría"
                      className="rounded p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 disabled:opacity-40"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setPorEliminar(cat)}
                      disabled={editandoId !== null || porEliminar !== null}
                      title="Eliminar categoría"
                      className="rounded p-1.5 text-zinc-500 hover:bg-red-50 hover:text-peligro disabled:opacity-40"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </Modal>
  );
}
