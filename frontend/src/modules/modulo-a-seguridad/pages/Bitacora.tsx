// Página de consulta de la bitácora (solo ADMIN): filtros por fecha, usuario,
// acción y entidad, con paginación. Objetivo: hallar quién hizo qué en < 1 minuto.
import { useBitacora } from "../hooks/useBitacora";

export default function Bitacora() {
  const { datos, filtros, cargando, error, aplicarFiltros } = useBitacora();

  const totalPaginas = datos ? Math.max(1, Math.ceil(datos.total / (filtros.tamano_pagina ?? 25))) : 1;
  const pagina = filtros.pagina ?? 1;

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">Bitácora de auditoría</h2>

      <div className="mb-4 grid gap-2 rounded-lg border bg-white p-3 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-xs text-gray-600">
          Desde
          <input
            type="datetime-local"
            className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            onChange={(e) => aplicarFiltros({ desde: e.target.value || undefined })}
          />
        </label>
        <label className="text-xs text-gray-600">
          Hasta
          <input
            type="datetime-local"
            className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            onChange={(e) => aplicarFiltros({ hasta: e.target.value || undefined })}
          />
        </label>
        <label className="text-xs text-gray-600">
          ID de usuario
          <input
            type="number"
            min={1}
            placeholder="ej. 3"
            className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            onChange={(e) =>
              aplicarFiltros({ usuario_id: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </label>
        <label className="text-xs text-gray-600">
          Acción
          <input
            placeholder="ej. login_fallido"
            className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            onChange={(e) => aplicarFiltros({ accion: e.target.value || undefined })}
          />
        </label>
        <label className="text-xs text-gray-600">
          Entidad
          <input
            placeholder="ej. usuarios, ventas"
            className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            onChange={(e) => aplicarFiltros({ entidad: e.target.value || undefined })}
          />
        </label>
      </div>

      {cargando && <p className="text-gray-500">Consultando…</p>}
      {error && <p className="text-red-600">{error}</p>}

      {datos && !cargando && (
        <>
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-600">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Usuario</th>
                  <th className="px-3 py-2">Rol</th>
                  <th className="px-3 py-2">Acción</th>
                  <th className="px-3 py-2">Entidad</th>
                  <th className="px-3 py-2">Detalle</th>
                  <th className="px-3 py-2">IP</th>
                </tr>
              </thead>
              <tbody>
                {datos.registros.map((r) => (
                  <tr key={r.id} className="border-t align-top">
                    <td className="whitespace-nowrap px-3 py-2 text-gray-500">
                      {r.created_at ? new Date(r.created_at).toLocaleString("es-PE") : "—"}
                    </td>
                    <td className="px-3 py-2">{r.usuario_id ?? "—"}</td>
                    <td className="px-3 py-2">{r.rol || "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.accion}</td>
                    <td className="px-3 py-2">
                      {r.entidad}
                      {r.entidad_id ? ` #${r.entidad_id}` : ""}
                    </td>
                    <td className="max-w-xs px-3 py-2 text-xs text-gray-600">
                      {r.motivo && <p>{r.motivo}</p>}
                      {r.valor_anterior && (
                        <p className="truncate" title={JSON.stringify(r.valor_anterior)}>
                          Antes: {JSON.stringify(r.valor_anterior)}
                        </p>
                      )}
                      {r.valor_nuevo && (
                        <p className="truncate" title={JSON.stringify(r.valor_nuevo)}>
                          Después: {JSON.stringify(r.valor_nuevo)}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{r.ip || "—"}</td>
                  </tr>
                ))}
                {datos.registros.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center text-gray-500">
                      Sin registros para los filtros elegidos.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
            <span>
              {datos.total} registro(s) — página {pagina} de {totalPaginas}
            </span>
            <div className="space-x-2">
              <button
                disabled={pagina <= 1}
                onClick={() => aplicarFiltros({ pagina: pagina - 1 })}
                className="rounded border px-3 py-1 disabled:opacity-40"
              >
                ← Anterior
              </button>
              <button
                disabled={pagina >= totalPaginas}
                onClick={() => aplicarFiltros({ pagina: pagina + 1 })}
                className="rounded border px-3 py-1 disabled:opacity-40"
              >
                Siguiente →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
