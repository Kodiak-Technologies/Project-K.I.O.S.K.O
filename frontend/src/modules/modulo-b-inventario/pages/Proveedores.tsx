// Página de gestión de proveedores (solo ADMIN).
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Pencil, Plus, Search, Users as UsersIcon } from "lucide-react";
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
import { useAuthContext } from "../../../shared/lib/auth-context";
import { FormularioProveedor } from "../components/FormularioProveedor";
import { ModalConfirmacion } from "../components/ModalConfirmacion";
import { PaginacionControles } from "../components/PaginacionControles";
import { useProveedores } from "../hooks/useProveedores";
import type { EdicionProveedor, NuevoProveedor, Proveedor } from "../types";

export default function Proveedores() {
  const { usuario } = useAuthContext();
  const esAdmin = usuario?.rol === "ADMIN";
  const { proveedores, paginados, cargando, error, noDisponible, recargar, crear, editar } =
    useProveedores();

  const [busqueda, setBusqueda] = useState("");
  const [filtroDeuda, setFiltroDeuda] = useState<"todos" | "con_deuda">("todos");
  const [filtroActivo, setFiltroActivo] = useState<"" | "true" | "false">("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [modalAlta, setModalAlta] = useState(false);
  const [editando, setEditando] = useState<Proveedor | null>(null);
  const [paraToggle, setParaToggle] = useState<Proveedor | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  useEffect(() => {
    const filtros: Record<string, unknown> = { page, page_size: pageSize };
    if (busqueda.trim()) filtros.search = busqueda.trim();
    if (filtroDeuda === "con_deuda") filtros.solo_con_deuda = true;
    if (filtroActivo) filtros.activo = filtroActivo === "true";
    void recargar(filtros as Parameters<typeof recargar>[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busqueda, filtroDeuda, filtroActivo, page, pageSize]);

  async function manejarCrear(datos: NuevoProveedor | EdicionProveedor) {
    setProcesando(true);
    setErrorAccion(null);
    try {
      await crear(datos as NuevoProveedor);
      setMensaje(`Proveedor '${(datos as NuevoProveedor).razon_social}' creado.`);
      setModalAlta(false);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
      throw e;
    } finally {
      setProcesando(false);
    }
  }

  async function manejarEditar(datos: NuevoProveedor | EdicionProveedor) {
    if (!editando) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await editar(editando.id, datos as EdicionProveedor);
      setMensaje(`Proveedor actualizado.`);
      setEditando(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
      throw e;
    } finally {
      setProcesando(false);
    }
  }

  async function manejarToggleActivo() {
    if (!paraToggle) return;
    setProcesando(true);
    setErrorAccion(null);
    try {
      await editar(paraToggle.id, { activo: !paraToggle.activo });
      setMensaje(`Proveedor '${paraToggle.razon_social}' ${paraToggle.activo ? "desactivado" : "activado"}.`);
      setParaToggle(null);
    } catch (e) {
      setErrorAccion(mensajeDeError(e));
    } finally {
      setProcesando(false);
    }
  }

  if (!esAdmin) {
    return (
      <div>
        <PageHeader titulo="Proveedores" />
        <Card sinPadding>
          <Alert tono="peligro">Esta sección es solo para ADMIN.</Alert>
        </Card>
      </div>
    );
  }

  if (noDisponible) {
    return (
      <div>
        <PageHeader titulo="Proveedores" />
        <Card sinPadding>
          <ModuloPendiente modulo="inventario" />
        </Card>
      </div>
    );
  }

  const columnas: Columna<Proveedor>[] = [
    { titulo: "Razón social", render: (p) => <Link to={`/proveedores/${p.id}`} className="font-medium text-zinc-800 hover:text-marca-secundario">{p.razon_social}</Link> },
    { titulo: "RUC", soloEscritorio: true, render: (p) => p.ruc ?? "—" },
    { titulo: "Teléfono", soloEscritorio: true, render: (p) => p.telefono ?? "—" },
    { titulo: "Email", soloEscritorio: true, render: (p) => p.email ?? "—" },
    {
      titulo: "Deuda",
      alinear: "derecha",
      render: (p) =>
        p.deuda_actual > 0 ? (
          <span className="font-semibold text-peligro">S/ {p.deuda_actual.toFixed(2)}</span>
        ) : (
          <span className="text-zinc-400">—</span>
        ),
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
            aria-label={`Editar ${p.razon_social}`}
            onClick={() => setEditando(p)}
            icono={<Pencil className="h-4 w-4" aria-hidden />}
          />
          <Button
            variante="secundario"
            compacto
            onClick={() => setParaToggle(p)}
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
        titulo="Proveedores"
        descripcion="Altas, deudas y pagos."
        acciones={
          <Button
            onClick={() => {
              setModalAlta(true);
              setErrorAccion(null);
            }}
            icono={<Plus className="h-4 w-4" aria-hidden />}
            className="w-full justify-center sm:w-auto"
          >
            Nuevo proveedor
          </Button>
        }

      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div className="relative min-w-64 flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" aria-hidden />
          <Input
            className="pl-9"
            placeholder="Buscar por razón social o RUC…"
            value={busqueda}
            onChange={(e) => {
              setBusqueda(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          label="Deuda"
          value={filtroDeuda}
          onChange={(e) => {
            setFiltroDeuda(e.target.value as "todos" | "con_deuda");
            setPage(1);
          }}
          className="max-w-xs"
        >
          <option value="todos">Todos</option>
          <option value="con_deuda">Solo con deuda</option>
        </Select>
        <Select
          label="Activo"
          value={filtroActivo}
          onChange={(e) => {
            setFiltroActivo(e.target.value as "" | "true" | "false");
            setPage(1);
          }}
          className="max-w-xs"
        >
          <option value="">Todos</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </Select>
      </div>

      {cargando && proveedores.length === 0 ? (
        <PageSpinner texto="Cargando proveedores…" />
      ) : error ? (
        <Alert tono="peligro">{error}</Alert>
      ) : (
        <Card sinPadding>
          <Table
            columnas={columnas}
            filas={proveedores}
            claveDe={(p) => p.id}
            vacio={
              <EmptyState
                icono={UsersIcon}
                titulo="Sin proveedores"
                descripcion="Crea el primer proveedor para registrar compras a crédito."
                accion={<Button onClick={() => setModalAlta(true)}>Nuevo proveedor</Button>}
              />
            }
          />
          <PaginacionControles
            paginados={paginados}
            page={page}
            pageSize={pageSize}
            onCambiarPage={setPage}
            onCambiarPageSize={setPageSize}
            etiqueta="proveedores"
          />
        </Card>
      )}

      {/* Modal: alta */}
      <Modal
        abierto={modalAlta}
        titulo="Nuevo proveedor"
        alCerrar={() => !procesando && setModalAlta(false)}
      >
        {errorAccion && <div className="mb-3"><Alert tono="peligro">{errorAccion}</Alert></div>}
        <FormularioProveedor
          inicial={{ razon_social: "", ruc: null, telefono: null, email: null, direccion: null }}
          onSubmit={manejarCrear}
          procesando={procesando}
        />
      </Modal>

      {/* Modal: edición */}
      <Modal
        abierto={editando !== null}
        titulo={`Editar '${editando?.razon_social ?? ""}'`}
        alCerrar={() => !procesando && setEditando(null)}
      >
        {errorAccion && <div className="mb-3"><Alert tono="peligro">{errorAccion}</Alert></div>}
        {editando && (
          <FormularioProveedor
            inicial={{
              razon_social: editando.razon_social,
              ruc: editando.ruc,
              telefono: editando.telefono,
              email: editando.email,
              direccion: editando.direccion,
            }}
            onSubmit={manejarEditar}
            procesando={procesando}
            esEdicion
          />
        )}
      </Modal>

      {/* Modal: activar/desactivar */}
      <ModalConfirmacion
        abierto={paraToggle !== null}
        titulo={paraToggle?.activo ? "Desactivar proveedor" : "Activar proveedor"}
        mensaje={
          paraToggle
            ? `¿${paraToggle.activo ? "Desactivar" : "Activar"} a '${paraToggle.razon_social}'?`
            : ""
        }
        textoConfirmar={paraToggle?.activo ? "Desactivar" : "Activar"}
        variante={paraToggle?.activo ? "peligro" : "primario"}
        cargando={procesando}
        alCancelar={() => setParaToggle(null)}
        alConfirmar={() => void manejarToggleActivo()}
      />
    </div>
  );
}
