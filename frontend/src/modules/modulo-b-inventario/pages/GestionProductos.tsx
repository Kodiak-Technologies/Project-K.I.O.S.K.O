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
  Select,
  Table,
  type Columna,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useCategorias } from "../hooks/useCategorias";
import { useProductos } from "../hooks/useProductos";
import type { Producto } from "../types";

const esquemaProducto = z.object({
  codigo: z.string().min(1, "Ingresa el código (o escanea el de barras)"),
  nombre: z.string().min(1, "Ingresa el nombre del producto"),
  precio: z.number().positive("El precio debe ser mayor a 0"),
  stock_minimo: z.number().int().min(0, "El stock mínimo no puede ser negativo"),
});

const FORMULARIO_VACIO = {
  codigo: "",
  nombre: "",
  categoria_id: null as number | null,
  precio: 0,
  stock_minimo: 0,
  stock_inicial: 0,
};

export default function GestionProductos() {
  const { productos, cargando, error, noDisponible, crear, actualizar } = useProductos();
  const { categorias, crear: crearCategoria } = useCategorias();

  const [editando, setEditando] = useState<Producto | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [nuevaCategoria, setNuevaCategoria] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

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
      precio: p.precio,
      stock_minimo: p.stock_minimo,
      stock_inicial: 0,
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
        const { stock_inicial: _sinStock, ...cambios } = formulario;
        await actualizar(editando.id, cambios);
        setMensaje(`Producto '${formulario.nombre}' actualizado.`);
      } else {
        await crear(formulario);
        setMensaje(`Producto '${formulario.nombre}' creado.`);
      }
      setModalAbierto(false);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  async function manejarNuevaCategoria() {
    if (!nuevaCategoria.trim()) return;
    try {
      await crearCategoria(nuevaCategoria.trim());
      setNuevaCategoria("");
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    }
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
    { titulo: "Código", render: (p) => <span className="font-mono text-xs text-zinc-500">{p.codigo}</span> },
    { titulo: "Producto", render: (p) => <span className="font-medium text-zinc-800">{p.nombre}</span> },
    { titulo: "Categoría", soloEscritorio: true, render: (p) => p.categoria ?? "—" },
    {
      titulo: "Precio",
      alinear: "derecha",
      render: (p) => <span className="tabular-nums">S/ {p.precio.toFixed(2)}</span>,
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
      </Card>

      <Modal
        abierto={modalAbierto}
        titulo={editando ? `Editar '${editando.nombre}'` : "Nuevo producto"}
        alCerrar={() => setModalAbierto(false)}
      >
        <form onSubmit={(e) => void manejarGuardar(e)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {/* autoFocus: el lector de barras/QR emula un teclado — con el cursor
                acá, escanear el producto llena el código solo. */}
            <Input
              label="Código (escanéalo o escríbelo)"
              requerido
              autoFocus={!editando}
              placeholder="ej. 7750100000000 o PAP-001"
              value={formulario.codigo}
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
              label="Precio (S/)"
              requerido
              type="number"
              step="0.10"
              min={0}
              value={formulario.precio || ""}
              onChange={(e) => setFormulario({ ...formulario, precio: Number(e.target.value) })}
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
          <Select
            label="Categoría"
            value={formulario.categoria_id ?? ""}
            onChange={(e) =>
              setFormulario({ ...formulario, categoria_id: e.target.value ? Number(e.target.value) : null })
            }
          >
            <option value="">Sin categoría</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </Select>
          <div className="flex items-end gap-2">
            <Input
              label="Nueva categoría"
              placeholder="ej. Abarrotes"
              value={nuevaCategoria}
              onChange={(e) => setNuevaCategoria(e.target.value)}
            />
            <Button type="button" variante="secundario" onClick={() => void manejarNuevaCategoria()}>
              Agregar
            </Button>
          </div>
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
