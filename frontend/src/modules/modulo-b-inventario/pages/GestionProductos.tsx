// Página de creación/edición de productos y categorías (solo ADMIN).
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { PackagePlus, Pencil } from "lucide-react";
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
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { PaginacionControles } from "../components/PaginacionControles";
import { SelectorCategoria } from "../components/SelectorCategoria";
import { SubirImagen } from "../components/SubirImagen";
import { useProductos } from "../hooks/useProductos";
import type { EdicionProducto, NuevoProducto, Producto } from "../types";

// PR3b: el form ahora separa precio_venta y precio_compra_actual, y tiene
// toggle `es_codigo_interno` + upload de `foto_url`.
const esquemaProducto = z
  .object({
    nombre: z.string().min(1, "Ingresa el nombre del producto"),
    codigo: z.string().nullable().optional(),
    precio_venta: z.number().positive("El precio de venta debe ser mayor a 0"),
    precio_compra_actual: z.number().min(0, "El precio de compra no puede ser negativo"),
    stock_minimo: z.number().int().min(0, "El stock mínimo no puede ser negativo"),
    stock_inicial: z.number().int().min(0).optional(),
    categoria_id: z.number().nullable().optional(),
    es_codigo_interno: z.boolean(),
    foto_url: z.string().nullable().optional(),
  })
  .superRefine((val, ctx) => {
    if (!val.es_codigo_interno && !val.codigo?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["codigo"],
        message: "Escaneá o escribí un código (o activá 'código interno').",
      });
    }
  });

interface FormProducto {
  codigo: string;
  nombre: string;
  categoria_id: number | null;
  precio_venta: number;
  precio_compra_actual: number;
  stock_minimo: number;
  stock_inicial: number;
  es_codigo_interno: boolean;
  foto_url: string | null;
}

const FORMULARIO_VACIO: FormProducto = {
  codigo: "",
  nombre: "",
  categoria_id: null,
  precio_venta: 0,
  precio_compra_actual: 0,
  stock_minimo: 0,
  stock_inicial: 0,
  es_codigo_interno: false,
  foto_url: null,
};

export default function GestionProductos() {
  const { productos, paginados, cargando, error, noDisponible, recargar, crear, actualizar } =
    useProductos();
  const [editando, setEditando] = useState<Producto | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [formulario, setFormulario] = useState<FormProducto>(FORMULARIO_VACIO);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  function abrirCrear() {
    setEditando(null);
    setFormulario(FORMULARIO_VACIO);
    setErrorAccion(null);
    setModalAbierto(true);
  }

  function abrirEditar(p: Producto) {
    setEditando(p);
    setFormulario({
      codigo: p.codigo,
      nombre: p.nombre,
      categoria_id: p.categoria_id,
      precio_venta: p.precio_venta ?? p.precio,
      precio_compra_actual: p.precio_compra_actual,
      stock_minimo: p.stock_minimo,
      stock_inicial: 0,
      es_codigo_interno: p.es_codigo_interno,
      foto_url: p.foto_url,
    });
    setErrorAccion(null);
    setModalAbierto(true);
  }

  async function manejarGuardar(evento: FormEvent) {
    evento.preventDefault();
    const validacion = esquemaProducto.safeParse(formulario);
    if (!validacion.success) {
      setErrorAccion(validacion.error.errors[0].message);
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      if (editando) {
        // El backend NO acepta precios en PATCH /productos/{id} (van por /precio).
        const cambios: EdicionProducto = {
          nombre: formulario.nombre.trim(),
          codigo: formulario.es_codigo_interno ? undefined : formulario.codigo.trim() || undefined,
          categoria_id: formulario.categoria_id,
          stock_minimo: formulario.stock_minimo,
          es_codigo_interno: formulario.es_codigo_interno,
          foto_url: formulario.foto_url,
        };
        await actualizar(editando.id, cambios);
        setMensaje(`Producto '${formulario.nombre}' actualizado.`);
      } else {
        const nuevo: NuevoProducto = {
          nombre: formulario.nombre.trim(),
          codigo: formulario.es_codigo_interno ? null : formulario.codigo.trim(),
          categoria_id: formulario.categoria_id,
          precio_venta: formulario.precio_venta,
          precio_compra_actual: formulario.precio_compra_actual,
          stock_minimo: formulario.stock_minimo,
          stock_inicial: formulario.stock_inicial,
          es_codigo_interno: formulario.es_codigo_interno,
          foto_url: formulario.foto_url,
        };
        await crear(nuevo);
        setMensaje(`Producto '${formulario.nombre}' creado.`);
      }
      setModalAbierto(false);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
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
        <PageHeader titulo="Gestión de productos" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario (Módulo B)" />
        </Card>
      </div>
    );
  }
  if (cargando) return <PageSpinner texto="Cargando productos…" />;
  if (error) return <Alert tono="peligro">{error}</Alert>;

  const columnas: Columna<Producto>[] = [
    {
      titulo: "Foto",
      render: (p) =>
        p.foto_url ? (
          <img src={p.foto_url} alt={p.nombre} className="h-8 w-8 rounded object-cover" />
        ) : (
          <div className="h-8 w-8 rounded bg-zinc-100" aria-hidden />
        ),
    },
    { titulo: "Código", render: (p) => <span className="font-mono text-xs text-zinc-500">{p.codigo}</span> },
    { titulo: "Producto", render: (p) => <span className="font-medium text-zinc-800">{p.nombre}</span> },
    { titulo: "Categoría", soloEscritorio: true, render: (p) => p.categoria_nombre ?? "—" },
    {
      titulo: "Precio venta",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums">S/ {(p.precio_venta ?? p.precio).toFixed(2)}</span>,
    },
    {
      titulo: "Precio compra",
      alinear: "derecha",
      soloEscritorio: true,
      render: (p) => <span className="tabular-nums">S/ {p.precio_compra_actual.toFixed(2)}</span>,
    },
    {
      titulo: "Stock",
      alinear: "derecha",
      soloEscritorio: true,
      render: (p) => <span className="tabular-nums">{p.stock}</span>,
    },
    {
      titulo: "Estado",
      render: (p) => <Badge tono={p.activo ? "exito" : "neutro"}>{p.activo ? "Activo" : "Inactivo"}</Badge>,
    },
    {
      titulo: "Acciones",
      render: (p) => (
        <div className="flex items-center gap-1">
          <Button
            variante="fantasma"
            compacto
            title="Editar"
            aria-label={`Editar ${p.nombre}`}
            onClick={() => abrirEditar(p)}
            icono={<Pencil className="h-4 w-4" aria-hidden />}
          />
          <Button
            variante="secundario"
            compacto
            onClick={() => void actualizar(p.id, { activo: !p.activo })}
          >
            {p.activo ? "Desactivar" : "Activar"}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Gestión de productos"
        descripcion="Alta, edición y precios del catálogo."
        acciones={
          <Button onClick={abrirCrear} icono={<PackagePlus className="h-4 w-4" aria-hidden />}>
            Nuevo producto
          </Button>
        }
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}

      <Card sinPadding>
        <Table
          columnas={columnas}
          filas={productos}
          claveDe={(p) => p.id}
          vacio={
            <EmptyState
              icono={PackagePlus}
              titulo="Sin productos"
              descripcion="Crea el primer producto del catálogo."
              accion={<Button onClick={abrirCrear}>Nuevo producto</Button>}
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

      <Modal
        abierto={modalAbierto}
        titulo={editando ? `Editar '${editando.nombre}'` : "Nuevo producto"}
        alCerrar={() => setModalAbierto(false)}
      >
        <form onSubmit={(e) => void manejarGuardar(e)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex items-center gap-2 self-end pb-2 sm:col-span-2">
              <input
                type="checkbox"
                checked={formulario.es_codigo_interno}
                onChange={(e) =>
                  setFormulario({
                    ...formulario,
                    es_codigo_interno: e.target.checked,
                    codigo: e.target.checked ? "" : formulario.codigo,
                  })
                }
                className="h-4 w-4 rounded border-zinc-300"
              />
              <span className="text-sm text-zinc-700">
                Es código interno (el backend autogenere el código)
              </span>
            </label>
            <Input
              label="Código (escanéalo o escríbelo)"
              requerido={!formulario.es_codigo_interno}
              autoFocus={!editando}
              placeholder={formulario.es_codigo_interno ? "(autogenerado)" : "ej. 7750100000000 o PAP-001"}
              value={formulario.codigo}
              disabled={formulario.es_codigo_interno}
              onChange={(e) => setFormulario({ ...formulario, codigo: e.target.value })}
            />
            <Input
              label="Nombre"
              requerido
              placeholder="ej. Arroz 5kg"
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
            />
            <Input
              label="Precio de venta (S/)"
              requerido
              type="number"
              step="0.10"
              min={0}
              disabled={!!editando}
              value={formulario.precio_venta || ""}
              onChange={(e) => setFormulario({ ...formulario, precio_venta: Number(e.target.value) })}
            />
            <Input
              label="Precio de compra actual (S/)"
              type="number"
              step="0.10"
              min={0}
              disabled={!!editando}
              value={formulario.precio_compra_actual || ""}
              onChange={(e) =>
                setFormulario({ ...formulario, precio_compra_actual: Number(e.target.value) })
              }
            />
            <Input
              label="Stock mínimo (alerta)"
              type="number"
              min={0}
              value={formulario.stock_minimo}
              onChange={(e) => setFormulario({ ...formulario, stock_minimo: Number(e.target.value) })}
            />
            {!editando && (
              <Input
                label="Cantidad inicial en almacén"
                type="number"
                min={0}
                value={formulario.stock_inicial}
                onChange={(e) => setFormulario({ ...formulario, stock_inicial: Number(e.target.value) })}
              />
            )}
          </div>
          {editando && (
            <p className="text-xs text-zinc-500">
              Para cambiar precios usá la acción "Cambiar precio" (próxima PR).
            </p>
          )}
          <SelectorCategoria
            value={formulario.categoria_id}
            onChange={(id) => setFormulario({ ...formulario, categoria_id: id })}
          />
          <SubirImagen
            carpeta="productos"
            label="Foto del producto (opcional)"
            ayuda="JPG o PNG. Se muestra en el POS."
            value={formulario.foto_url}
            onChange={(url) => setFormulario({ ...formulario, foto_url: url })}
          />
          {errorAccion && <Alert tono="peligro">{errorAccion}</Alert>}
          <div className="flex justify-end gap-2">
            <Button type="button" variante="secundario" onClick={() => setModalAbierto(false)}>
              Cancelar
            </Button>
            <Button type="submit" cargando={procesando}>
              {editando ? "Guardar cambios" : "Crear producto"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
