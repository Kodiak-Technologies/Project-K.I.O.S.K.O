import { useState } from "react";
import { AlertCircle } from "lucide-react";
import logoKodiak from "../../../assets/KODIAK.png";
import paquete from "../../../package.json";
import { Modal } from "./ui";

export function AcercaDelSistema() {
  const [abierto, setAbierto] = useState(false);

  return (
    <>
      {/* Botón en modo responsivo: Casi transparente en reposo para no tapar texto (S/ 53.20) */}
      <button
        type="button"
        onClick={() => setAbierto(true)}
        title="Acerca del sistema"
        aria-label="Acerca del sistema"
        className="fixed right-0 bottom-24 z-30 flex items-center justify-center rounded-l-full border-y border-l border-zinc-300/40 bg-white/15 p-2.5 opacity-35 transition-all hover:bg-white hover:opacity-100 hover:shadow-lg focus:outline-none sm:bottom-4 sm:right-4 sm:h-9 sm:w-9 sm:rounded-full sm:border-zinc-200 sm:bg-white sm:p-0 sm:opacity-100"
      >
        <AlertCircle
          style={{ color: "var(--color-secundario)" }}
          className="h-5 w-5 shrink-0 transition-transform hover:scale-110 sm:h-4 sm:w-4"
          aria-hidden
        />
      </button>

      <Modal abierto={abierto} titulo="Acerca del sistema" alCerrar={() => setAbierto(false)}>
        <div className="flex flex-col items-center gap-4 py-2 text-center">
          <img src={logoKodiak} alt="KODIAK Technologies" className="h-12 max-w-full object-contain" />
          <div>
            <p className="text-lg font-semibold text-zinc-900">K.I.O.S.K.O</p>
            <p className="mt-1 text-sm text-zinc-600">
              Sistema de ventas e inventario para tiendas: punto de venta, caja, stock con
              aprobaciones, comprobantes, reportes y auditoría completa.
            </p>
          </div>
          <div className="text-xs text-zinc-400">
            <p>Versión {paquete.version}</p>
            <p className="mt-0.5">Desarrollado por KODIAK Technologies</p>
          </div>
        </div>
      </Modal>
    </>
  );
}
