// Adaptador de impresión de tickets (HU-C05, RF-11).
//
// Estrategia GENÉRICA: se imprime un HTML con ancho de papel térmico (58 u 80 mm)
// a través del diálogo del sistema. Cualquier impresora térmica instalada con su
// driver (la vía estándar en Windows/Android para equipos ESC/POS) lo recibe como
// una página más, sin depender de la marca. La venta NUNCA depende del ticket:
// imprimir es opcional y posterior a confirmar.
import type { Venta } from "../types";

export type AnchoPapel = "58" | "80";

const CLAVE_ANCHO = "kiosko_ticket_ancho";

export const preferenciaPapel = {
  obtener(): AnchoPapel {
    return localStorage.getItem(CLAVE_ANCHO) === "58" ? "58" : "80";
  },
  guardar(ancho: AnchoPapel) {
    localStorage.setItem(CLAVE_ANCHO, ancho);
  },
};

interface DatosNegocio {
  nombre: string;
  logoUrl?: string;
}

function escapar(texto: string): string {
  return texto.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function htmlTicket(venta: Venta, negocio: DatosNegocio, ancho: AnchoPapel): string {
  // Ancho imprimible real: ~48 mm en papel de 58, ~72 mm en papel de 80.
  const anchoMm = ancho === "58" ? 48 : 72;
  const fecha = venta.created_at ? new Date(venta.created_at) : new Date();

  const lineas = venta.items
    .map(
      (i) => `
      <tr>
        <td class="cant">${i.cantidad}×</td>
        <td class="nom">${escapar(i.nombre)}<br/><span class="pu">S/ ${i.precio_unitario.toFixed(2)} c/u</span></td>
        <td class="sub">S/ ${(i.precio_unitario * i.cantidad).toFixed(2)}</td>
      </tr>`
    )
    .join("");

  const pagos = venta.pagos
    .map(
      (p) => `
      <div class="fila"><span>${escapar(p.metodo)}</span><span>S/ ${p.monto.toFixed(2)}</span></div>
      ${p.monto_recibido !== null ? `<div class="fila chica"><span>Recibido</span><span>S/ ${p.monto_recibido.toFixed(2)}</span></div>` : ""}`
    )
    .join("");

  return `<!doctype html><html><head><meta charset="utf-8"><title>Ticket venta ${venta.id}</title>
  <style>
    @page { size: ${ancho}mm auto; margin: 0; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { width: ${anchoMm}mm; font-family: "Courier New", monospace; font-size: 11px;
           color: #000; padding: 2mm 1mm; }
    .centro { text-align: center; }
    .logo { max-width: 18mm; max-height: 18mm; object-fit: contain; }
    h1 { font-size: 13px; text-transform: uppercase; }
    .sep { border-top: 1px dashed #000; margin: 4px 0; }
    table { width: 100%; border-collapse: collapse; }
    td { vertical-align: top; padding: 1px 0; }
    .cant { width: 9%; }
    .nom { padding-right: 4px; }
    .pu { font-size: 9px; }
    .sub { text-align: right; white-space: nowrap; }
    .fila { display: flex; justify-content: space-between; }
    .fila.chica { font-size: 9px; }
    .total { font-size: 14px; font-weight: bold; }
    .pie { margin-top: 6px; font-size: 9px; }
  </style></head><body>
    <div class="centro">
      ${negocio.logoUrl ? `<img class="logo" src="${negocio.logoUrl}" alt=""/>` : ""}
      <h1>${escapar(negocio.nombre)}</h1>
      <div>${
        venta.id === 0
          ? "Ticket de venta (pendiente de sincronizar)"
          : `Ticket de venta N° ${String(venta.id).padStart(6, "0")}`
      }</div>
      <div>${fecha.toLocaleString("es-PE")}</div>
      <div>Atendido por: ${escapar(venta.vendedor)}</div>
    </div>
    <div class="sep"></div>
    <table>${lineas}</table>
    <div class="sep"></div>
    <div class="fila total"><span>TOTAL</span><span>S/ ${venta.total.toFixed(2)}</span></div>
    ${pagos}
    ${venta.vuelto > 0 ? `<div class="fila"><span>Vuelto</span><span>S/ ${venta.vuelto.toFixed(2)}</span></div>` : ""}
    <div class="sep"></div>
    <div class="centro pie">¡Gracias por su compra!<br/>Comprobante interno — no es documento tributario</div>
  </body></html>`;
}

/** Imprime el ticket en un iframe oculto: no navega ni bloquea la venta. */
export function imprimirTicket(venta: Venta, negocio: DatosNegocio, ancho: AnchoPapel): void {
  const iframe = document.createElement("iframe");
  iframe.setAttribute("aria-hidden", "true");
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  document.body.appendChild(iframe);

  const ventana = iframe.contentWindow;
  if (!ventana) return;
  ventana.document.open();
  ventana.document.write(htmlTicket(venta, negocio, ancho));
  ventana.document.close();
  // Pequeña espera para que cargue el logo antes de abrir el diálogo.
  setTimeout(() => {
    ventana.focus();
    ventana.print();
    setTimeout(() => document.body.removeChild(iframe), 60_000);
  }, 150);
}
