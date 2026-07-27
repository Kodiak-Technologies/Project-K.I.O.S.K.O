import { useState } from "react";
import { AlertCircle } from "lucide-react";
import logoKodiak from "../../../assets/KODIAK.png";
import paquete from "../../../package.json";
import { Modal } from "./ui";

export function AcercaDelSistema() {
  const [abierto, setAbierto] = useState(false);

  return (
    <>
      <button
        onClick={() => setAbierto(true)}
        title="Acerca del sistema"
        aria-label="Acerca del sistema"
        className="fixed bottom-3 right-3 z-30 flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-white shadow-md transition-all hover:bg-zinc-50 hover:shadow-lg focus:outline-none"
      >
        <AlertCircle style={{ color: "var(--color-secundario)" }} className="h-4 w-4 shrink-0" aria-hidden />
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
