// Botón flotante "!" (abajo a la derecha en toda la app autenticada): abre el
// "Acerca del sistema" con nombre, descripción, versión y la firma de KODIAK.
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
        className="fixed bottom-4 right-4 z-30 flex h-11 w-11 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-400 shadow-tarjeta hover:text-zinc-600 hover:shadow-lg"
      >
        <AlertCircle className="h-5 w-5" aria-hidden />
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
