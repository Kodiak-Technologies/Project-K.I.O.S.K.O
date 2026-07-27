// Página de configuración e identidad visual (solo ADMIN): nombre, logo, colores,
// tipografía y parámetros de seguridad (TTL de sesión, intentos, bloqueo).
import { useEffect, useRef, useState, type FormEvent } from "react";
import { CheckCircle2, ImagePlus, Loader2, Save, Trash2, Upload } from "lucide-react";
import {
  Alert,
  Button,
  Card,
  ColorPicker,
  Input,
  PageHeader,
  PageSpinner,
  Select,
} from "../../../shared/components/ui";
import { mensajeDeError, normalizarImagenUrl } from "../../../shared/lib/http-client";
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
  const [subiendoLogo, setSubiendoLogo] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);

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
    setSubiendoLogo(true);
    try {
      const actualizada = await configuracionHttpAdapter.subirLogo(archivo);
      setConfig(actualizada);
      aplicarTema({ logoUrl: actualizada.logo_url });
      setMensaje("Logo actualizado.");
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setSubiendoLogo(false);
      if (logoInputRef.current) logoInputRef.current.value = "";
    }
  }

  async function manejarEliminarLogo() {
    setError(null);
    setSubiendoLogo(true);
    try {
      const actualizada = await configuracionHttpAdapter.actualizar({ logo_url: "" });
      setConfig(actualizada);
      aplicarTema({ logoUrl: actualizada.logo_url });
      setMensaje("Logo eliminado.");
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setSubiendoLogo(false);
    }
  }

  if (!config && !error) return <PageSpinner texto="Cargando configuración…" />;
  if (!config) return <Alert tono="peligro">{error}</Alert>;

  return (
    <div className="max-w-6xl">
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

      <form onSubmit={(e) => void manejarGuardar(e)} className="space-y-5">
        <div className="grid gap-5 lg:grid-cols-3 lg:items-stretch">
          <Card
            titulo="Identidad visual"
            descripcion="Cómo se ve el sistema para todo el personal."
            className="lg:col-span-2 flex flex-col"
            cuerpoClassName="flex flex-1 flex-col"
          >
            <div className="flex flex-1 flex-col justify-between gap-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Nombre comercial"
                  value={config.nombre_negocio}
                  onChange={(e) => actualizarCampo("nombre_negocio", e.target.value)}
                />
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

              <div>
                <span className="mb-1.5 block text-sm font-medium text-zinc-700">Logo del negocio</span>
                {config.logo_url ? (
                  <div className="flex flex-wrap items-center gap-4 rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                    <div className="relative flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-zinc-200 bg-white p-2">
                      <img
                        src={normalizarImagenUrl(config.logo_url)}
                        alt="Logo del negocio"
                        className="h-full w-full object-contain"
                      />
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col justify-center gap-0.5">
                      <div className="flex items-center gap-1.5 text-sm font-semibold text-zinc-800">
                        <CheckCircle2 className="h-4 w-4 text-exito-intenso" />
                        <span>Logo cargado</span>
                      </div>
                      <p className="text-xs text-zinc-500">Se muestra en el encabezado y en las boletas.</p>
                    </div>
                    <div className="ml-auto flex shrink-0 items-center gap-2">
                      <Button
                        type="button"
                        variante="secundario"
                        compacto
                        disabled={subiendoLogo}
                        onClick={() => logoInputRef.current?.click()}
                        icono={
                          subiendoLogo ? (
                            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                          ) : (
                            <Upload className="h-4 w-4" aria-hidden />
                          )
                        }
                      >
                        Cambiar
                      </Button>
                      <Button
                        type="button"
                        variante="secundario"
                        compacto
                        disabled={subiendoLogo}
                        onClick={() => void manejarEliminarLogo()}
                        className="text-peligro"
                        icono={<Trash2 className="h-4 w-4" aria-hidden />}
                      >
                        Eliminar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <button
                      type="button"
                      onClick={() => logoInputRef.current?.click()}
                      disabled={subiendoLogo}
                      className="flex min-h-[110px] w-full items-center justify-center gap-2 rounded-xl border border-dashed border-zinc-300 bg-white px-4 py-4 text-sm font-medium text-zinc-800 shadow-sm transition hover:border-zinc-400 hover:bg-zinc-50 focus:outline-none focus:ring-1 focus:ring-zinc-500 disabled:opacity-50"
                    >
                      {subiendoLogo ? (
                        <Loader2 className="h-4 w-4 animate-spin text-zinc-500" aria-hidden />
                      ) : (
                        <ImagePlus className="h-4 w-4 text-zinc-500" aria-hidden />
                      )}
                      <span>{subiendoLogo ? "Subiendo logo…" : "Adjuntar logo del negocio"}</span>
                    </button>
                    <p className="mt-1 text-xs text-zinc-400">PNG, JPG, WebP o SVG · máx. 500 KB.</p>
                  </div>
                )}
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/png,image/jpeg,.jpg,.jpeg,.png,.webp,.svg"
                  onChange={(e) => void manejarLogo(e.target.files?.[0])}
                  className="hidden"
                />
              </div>

              <div>
                <span className="mb-2 block text-sm font-medium text-zinc-700">Colores de marca</span>
                <div className="grid gap-3 sm:grid-cols-2">
                  <ColorPicker
                    label="Color primario"
                    descripcion="Botones y acentos"
                    value={config.color_primario}
                    onChange={(hex) => actualizarCampo("color_primario", hex)}
                  />
                  <ColorPicker
                    label="Color secundario"
                    descripcion="Íconos y detalles"
                    value={config.color_secundario}
                    onChange={(hex) => actualizarCampo("color_secundario", hex)}
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card
            titulo="Seguridad de sesiones"
            descripcion="Cuánto duran las sesiones y el bloqueo por intentos fallidos."
            className="lg:col-span-1 h-full"
          >
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
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
        </div>

        <Button type="submit" cargando={guardando} className="w-full" icono={<Save className="h-4 w-4" aria-hidden />}>
          {guardando ? "Guardando…" : "Guardar configuración"}
        </Button>
      </form>
    </div>
  );
}
