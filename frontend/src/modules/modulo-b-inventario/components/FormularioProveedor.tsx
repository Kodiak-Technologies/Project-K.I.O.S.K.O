// Formulario de Proveedor (alta o edición).
// Reutilizado en Proveedores (modal alta y modal edición) y ProveedorDetalle.
import { useState, useEffect } from "react";
import { Input } from "../../../shared/components/ui";
import type { EdicionProveedor, NuevoProveedor } from "../types";

interface Props {
  /** Valores iniciales (vacío para alta). */
  inicial: NuevoProveedor | EdicionProveedor;
  onSubmit: (datos: NuevoProveedor | EdicionProveedor) => Promise<void>;
  procesando: boolean;
  /** Si es edición, valida `razon_social` mínima; si es alta, también. */
  esEdicion?: boolean;
}

const VACIO: NuevoProveedor = {
  razon_social: "",
  ruc: null,
  telefono: null,
  email: null,
  direccion: null,
};

export function FormularioProveedor({ inicial, onSubmit, procesando, esEdicion }: Props) {
  const [form, setForm] = useState<NuevoProveedor | EdicionProveedor>({ ...VACIO, ...inicial });
  const [errores, setErrores] = useState<Record<string, string>>({});

  // Re-sincroniza si cambian los valores iniciales (ej. al cambiar de proveedor a editar).
  useEffect(() => {
    setForm({ ...VACIO, ...inicial });
    setErrores({});
  }, [inicial]);

  function validar(): boolean {
    const e: Record<string, string> = {};
    if (!("razon_social" in form) || !form.razon_social?.trim()) {
      e.razon_social = "La razón social es obligatoria.";
    }
    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) {
      e.email = "Email inválido.";
    }
    setErrores(e);
    return Object.keys(e).length === 0;
  }

  async function manejarSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validar()) return;
    // Limpiamos strings vacíos a null para no mandar `""` al backend.
    const limpio: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(form)) {
      if (typeof v === "string") limpio[k] = v.trim() ? v.trim() : null;
      else limpio[k] = v;
    }
    try {
      await onSubmit(limpio as NuevoProveedor | EdicionProveedor);
    } catch {
      // El padre maneja el error en su propio state.
    }
  }

  return (
    <form onSubmit={(e) => void manejarSubmit(e)} className="space-y-3">
      <Input
        label="Razón social"
        requerido
        value={form.razon_social ?? ""}
        onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
        error={errores.razon_social}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="RUC (opcional)"
          maxLength={20}
          value={form.ruc ?? ""}
          onChange={(e) => setForm({ ...form, ruc: e.target.value || null })}
        />
        <Input
          label="Teléfono (opcional)"
          maxLength={20}
          value={form.telefono ?? ""}
          onChange={(e) => setForm({ ...form, telefono: e.target.value || null })}
        />
      </div>
      <Input
        label="Email (opcional)"
        type="email"
        maxLength={120}
        value={form.email ?? ""}
        onChange={(e) => setForm({ ...form, email: e.target.value || null })}
        error={errores.email}
      />
      <Input
        label="Dirección (opcional)"
        maxLength={500}
        value={form.direccion ?? ""}
        onChange={(e) => setForm({ ...form, direccion: e.target.value || null })}
      />
      <div className="flex justify-end gap-2 pt-1">
        <button
          type="submit"
          disabled={procesando}
          className="inline-flex min-h-tactil items-center justify-center gap-2 rounded-lg bg-marca px-4 py-2 text-sm font-medium text-white hover:opacity-85 disabled:opacity-60"
        >
          {procesando ? "Guardando…" : esEdicion ? "Guardar cambios" : "Crear proveedor"}
        </button>
      </div>
    </form>
  );
}
