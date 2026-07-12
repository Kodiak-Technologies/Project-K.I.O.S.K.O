// Página de configuración e identidad visual (solo ADMIN): nombre, logo, colores,
// tipografía y parámetros de seguridad (TTL de sesión, intentos, bloqueo).
import { useEffect, useState, type FormEvent } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { useTema } from "../../../shared/lib/theme-context";
import { configuracionHttpAdapter } from "../services/configuracion.http-adapter";
import type { Configuracion as ConfiguracionDto } from "../types";

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

  if (!config && !error) return <p className="text-gray-500">Cargando configuración…</p>;
  if (!config) return <p className="text-red-600">{error}</p>;

  return (
    <div className="max-w-2xl">
      <h2 className="mb-4 text-lg font-semibold">Configuración del negocio</h2>

      {mensaje && <p className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-700">{mensaje}</p>}
      {error && <p className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <form onSubmit={manejarGuardar} className="space-y-6">
        <fieldset className="rounded-lg border bg-white p-4">
          <legend className="px-1 text-sm font-medium text-gray-700">Identidad visual</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              Nombre comercial
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={config.nombre_negocio}
                onChange={(e) => actualizarCampo("nombre_negocio", e.target.value)}
              />
            </label>
            <label className="text-sm">
              Logo (PNG/JPG/WebP/SVG, máx. 500 KB)
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                className="mt-1 w-full text-sm"
                onChange={(e) => void manejarLogo(e.target.files?.[0])}
              />
            </label>
            <label className="flex items-center justify-between text-sm">
              Color primario
              <input
                type="color"
                value={config.color_primario}
                onChange={(e) => actualizarCampo("color_primario", e.target.value)}
              />
            </label>
            <label className="flex items-center justify-between text-sm">
              Color secundario
              <input
                type="color"
                value={config.color_secundario}
                onChange={(e) => actualizarCampo("color_secundario", e.target.value)}
              />
            </label>
            <label className="text-sm sm:col-span-2">
              Tipografía
              <select
                className="mt-1 w-full rounded border px-3 py-2"
                value={config.tipografia}
                onChange={(e) => actualizarCampo("tipografia", e.target.value)}
              >
                {["Inter", "Roboto", "Poppins", "Lato", "Montserrat", "system-ui"].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
          </div>
        </fieldset>

        <fieldset className="rounded-lg border bg-white p-4">
          <legend className="px-1 text-sm font-medium text-gray-700">Seguridad de sesiones</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              Sesión ADMIN (minutos)
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border px-3 py-2"
                value={config.session_ttl_admin_minutos}
                onChange={(e) => actualizarCampo("session_ttl_admin_minutos", Number(e.target.value))}
              />
              <span className="text-xs text-gray-500">43200 = 30 días</span>
            </label>
            <label className="text-sm">
              Sesión CAJERO (minutos)
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border px-3 py-2"
                value={config.session_ttl_cajero_minutos}
                onChange={(e) => actualizarCampo("session_ttl_cajero_minutos", Number(e.target.value))}
              />
              <span className="text-xs text-gray-500">720 = 12 horas</span>
            </label>
            <label className="text-sm">
              Intentos máximos de login
              <input
                type="number"
                min={1}
                max={10}
                className="mt-1 w-full rounded border px-3 py-2"
                value={config.max_intentos_login}
                onChange={(e) => actualizarCampo("max_intentos_login", Number(e.target.value))}
              />
            </label>
            <label className="text-sm">
              Minutos de bloqueo
              <input
                type="number"
                min={1}
                max={1440}
                className="mt-1 w-full rounded border px-3 py-2"
                value={config.minutos_bloqueo}
                onChange={(e) => actualizarCampo("minutos_bloqueo", Number(e.target.value))}
              />
            </label>
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={guardando}
          className="rounded-lg px-4 py-2 font-medium text-white disabled:opacity-60"
          style={{ backgroundColor: "var(--color-primario)" }}
        >
          {guardando ? "Guardando…" : "Guardar configuración"}
        </button>
      </form>
    </div>
  );
}
