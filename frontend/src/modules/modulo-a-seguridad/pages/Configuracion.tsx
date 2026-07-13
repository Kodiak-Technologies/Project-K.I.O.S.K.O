// Página de configuración e identidad visual (solo ADMIN): nombre, logo, colores,
// tipografía y parámetros de seguridad (TTL de sesión, intentos, bloqueo).
import { useEffect, useState, type FormEvent } from "react";
import { Save } from "lucide-react";
import {
  Alert,
  Button,
  Card,
  Input,
  PageHeader,
  PageSpinner,
  Select,
} from "../../../shared/components/ui";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useTema } from "../../../shared/lib/theme-context";
import { configuracionHttpAdapter } from "../services/configuracion.http-adapter";
import type { Configuracion as ConfiguracionDto } from "../types";

const TIPOGRAFIAS = ["Inter", "Roboto", "Poppins", "Lato", "Montserrat", "system-ui"];

export default function Configuracion() {
  const { aplicarTema } = useTema();
  const [config, setConfig] = useState<ConfiguracionDto | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    configuracionHttpAdapter.obtener().then(setConfig).catch((e) => setError(mensajeDeError(e)));
  }, []);

  function actualizarCampo<K extends keyof ConfiguracionDto>(campo: K, valor: ConfiguracionDto[K]) {
    if (config) setConfig({ ...config, [campo]: valor });
  }

  async function manejarGuardar(evento: FormEvent) {
    evento.preventDefault();
    if (!config) return;
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const actualizada = await configuracionHttpAdapter.actualizar({
        nombre_negocio: config.nombre_negocio,
        color_primario: config.color_primario,
        color_secundario: config.color_secundario,
        tipografia: config.tipografia,
        session_ttl_admin_minutos: config.session_ttl_admin_minutos,
        session_ttl_cajero_minutos: config.session_ttl_cajero_minutos,
        max_intentos_login: config.max_intentos_login,
        minutos_bloqueo: config.minutos_bloqueo,
      });
      setConfig(actualizada);
      aplicarTema({
        nombreNegocio: actualizada.nombre_negocio,
        colorPrimario: actualizada.color_primario,
        colorSecundario: actualizada.color_secundario,
        tipografia: actualizada.tipografia,
        logoUrl: actualizada.logo_url,
      });
      setMensaje("Configuración guardada. El cambio quedó registrado en la bitácora.");
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setGuardando(false);
    }
  }

  async function manejarLogo(archivo: File | undefined) {
    if (!archivo) return;
    setError(null);
    try {
      const actualizada = await configuracionHttpAdapter.subirLogo(archivo);
      setConfig(actualizada);
      aplicarTema({ logoUrl: actualizada.logo_url });
      setMensaje("Logo actualizado.");
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }

  if (!config && !error) return <PageSpinner texto="Cargando configuración…" />;
  if (!config) return <Alert tono="peligro">{error}</Alert>;

  return (
    <div className="max-w-2xl">
      <PageHeader
        titulo="Configuración del negocio"
        descripcion="Identidad visual y parámetros de seguridad; aplican para todos los usuarios."
      />

      {mensaje && (
        <div className="mb-4">
          <Alert tono="exito">{mensaje}</Alert>
        </div>
      )}
      {error && (
        <div className="mb-4">
          <Alert tono="peligro">{error}</Alert>
        </div>
      )}

      <form onSubmit={(e) => void manejarGuardar(e)} className="space-y-4">
        <Card titulo="Identidad visual" descripcion="Cómo se ve el sistema para todo el personal.">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Nombre comercial"
              value={config.nombre_negocio}
              onChange={(e) => actualizarCampo("nombre_negocio", e.target.value)}
            />
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-zinc-700">
                Logo (PNG/JPG/WebP/SVG, máx. 500 KB)
              </span>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                className="w-full text-sm text-zinc-600 file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-zinc-700 hover:file:bg-zinc-200"
                onChange={(e) => void manejarLogo(e.target.files?.[0])}
              />
            </label>
            <label className="flex min-h-tactil items-center justify-between rounded-lg border border-zinc-300 px-3 text-sm text-zinc-700">
              Color primario (acentos)
              <input
                type="color"
                value={config.color_primario}
                onChange={(e) => actualizarCampo("color_primario", e.target.value)}
              />
            </label>
            <label className="flex min-h-tactil items-center justify-between rounded-lg border border-zinc-300 px-3 text-sm text-zinc-700">
              Color secundario
              <input
                type="color"
                value={config.color_secundario}
                onChange={(e) => actualizarCampo("color_secundario", e.target.value)}
              />
            </label>
            <div className="sm:col-span-2">
              <Select
                label="Tipografía"
                value={config.tipografia}
                onChange={(e) => actualizarCampo("tipografia", e.target.value)}
              >
                {TIPOGRAFIAS.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </Select>
            </div>
          </div>
        </Card>

        <Card titulo="Seguridad de sesiones" descripcion="Cuánto duran las sesiones y el bloqueo por intentos fallidos.">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Input
                label="Sesión ADMIN (minutos)"
                type="number"
                min={1}
                value={config.session_ttl_admin_minutos}
                onChange={(e) => actualizarCampo("session_ttl_admin_minutos", Number(e.target.value))}
              />
              <p className="mt-1 text-xs text-zinc-500">43200 = 30 días</p>
            </div>
            <div>
              <Input
                label="Sesión CAJERO (minutos)"
                type="number"
                min={1}
                value={config.session_ttl_cajero_minutos}
                onChange={(e) => actualizarCampo("session_ttl_cajero_minutos", Number(e.target.value))}
              />
              <p className="mt-1 text-xs text-zinc-500">720 = 12 horas</p>
            </div>
            <Input
              label="Intentos máximos de login"
              type="number"
              min={1}
              max={10}
              value={config.max_intentos_login}
              onChange={(e) => actualizarCampo("max_intentos_login", Number(e.target.value))}
            />
            <Input
              label="Minutos de bloqueo"
              type="number"
              min={1}
              max={1440}
              value={config.minutos_bloqueo}
              onChange={(e) => actualizarCampo("minutos_bloqueo", Number(e.target.value))}
            />
          </div>
        </Card>

        <Button type="submit" cargando={guardando} icono={<Save className="h-4 w-4" aria-hidden />}>
          {guardando ? "Guardando…" : "Guardar configuración"}
        </Button>
      </form>
    </div>
  );
}
