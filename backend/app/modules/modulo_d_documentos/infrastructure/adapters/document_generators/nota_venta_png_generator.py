import io

from PIL import Image, ImageDraw, ImageFont


class NotaVentaPngGenerator:
    ANCHO = 500
    MARGEN = 20
    MARGEN_DERECHA = 20

    async def generar(
        self,
        numero: str,
        total: float,
        fecha: str,
        productos: list[dict],
        nombre_negocio: str = "Mi Tienda",
        vendedor: str = "",
        pagos: list[dict] | None = None,
        vuelto: float = 0,
    ) -> bytes:
        pagos = pagos or []

        try:
            font_title = ImageFont.truetype("cour.ttf", 16)
            font_normal = ImageFont.truetype("cour.ttf", 12)
            font_small = ImageFont.truetype("cour.ttf", 10)
            font_total = ImageFont.truetype("courbd.ttf", 16)
        except OSError:
            try:
                font_title = ImageFont.truetype("arial.ttf", 16)
                font_normal = ImageFont.truetype("arial.ttf", 12)
                font_small = ImageFont.truetype("arial.ttf", 10)
                font_total = ImageFont.truetype("arialbd.ttf", 16)
            except OSError:
                font_title = ImageFont.load_default()
                font_normal = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_total = ImageFont.load_default()

        alto_estimado = 280 + len(productos) * 22 + len(pagos) * 18
        img = Image.new("RGB", (self.ANCHO, alto_estimado), color="white")
        draw = ImageDraw.Draw(img)

        ancho_util = self.ANCHO - self.MARGEN - self.MARGEN_DERECHA
        y = 15

        def centrar(texto: str, font, yPos: int, fill="black") -> int:
            bbox = draw.textbbox((0, 0), texto, font=font)
            tw = bbox[2] - bbox[0]
            x = (self.ANCHO - tw) // 2
            draw.text((x, yPos), texto, fill=fill, font=font)
            return yPos + (bbox[3] - bbox[1]) + 4

        def linea_separadora(yPos: int) -> int:
            draw.text((self.MARGEN, yPos), "-" * 40, fill="gray", font=font_small)
            return yPos + 16

        y = centrar(nombre_negocio.upper(), font_title, y)
        y += 2
        y = centrar(f"NOTA DE VENTA N {numero}", font_normal, y)
        y = centrar(fecha, font_normal, y)
        if vendedor:
            y = centrar(f"Atendido por: {vendedor}", font_small, y)
        y += 4
        y = linea_separadora(y)

        for prod in productos:
            nombre = prod.get("nombre", "")
            cantidad = prod.get("cantidad", 0)
            precio = prod.get("precio_unitario", 0)
            subtotal = precio * cantidad

            linea_izq = f"{cantidad}x {nombre}"
            linea_der = f"S/ {subtotal:.2f}"

            bbox_izq = draw.textbbox((0, 0), linea_izq, font=font_normal)
            bbox_der = draw.textbbox((0, 0), linea_der, font=font_normal)
            ancho_izq = bbox_izq[2] - bbox_izq[0]
            ancho_der = bbox_der[2] - bbox_der[0]

            x_izq = self.MARGEN
            x_der = self.ANCHO - self.MARGEN_DERECHA - ancho_der

            draw.text((x_izq, y), linea_izq, fill="black", font=font_normal)
            draw.text((x_der, y), linea_der, fill="black", font=font_normal)
            y += 18

            precio_linea = f"   S/ {precio:.2f} c/u"
            draw.text((self.MARGEN, y), precio_linea, fill="gray", font=font_small)
            y += 16

        y += 4
        y = linea_separadora(y)
        y += 2

        total_text = f"TOTAL: S/ {total:.2f}"
        bbox_total = draw.textbbox((0, 0), total_text, font=font_total)
        tw = bbox_total[2] - bbox_total[0]
        x_total = (self.ANCHO - tw) // 2
        draw.text((x_total, y), total_text, fill="black", font=font_total)
        y += bbox_total[3] - bbox_total[1] + 10

        if pagos:
            y = linea_separadora(y)
            for pago in pagos:
                metodo = pago.get("metodo", "")
                monto = pago.get("monto", 0)
                monto_recibido = pago.get("monto_recibido")

                linea_pago = f"  {metodo}"
                monto_pago = f"S/ {monto:.2f}"

                bbox_metodo = draw.textbbox((0, 0), linea_pago, font=font_normal)
                bbox_monto = draw.textbbox((0, 0), monto_pago, font=font_normal)

                draw.text((self.MARGEN, y), linea_pago, fill="black", font=font_normal)
                draw.text(
                    (self.ANCHO - self.MARGEN_DERECHA - (bbox_monto[2] - bbox_monto[0]), y),
                    monto_pago, fill="black", font=font_normal,
                )
                y += 18

                if monto_recibido is not None:
                    rec_text = f"    Recibido: S/ {monto_recibido:.2f}"
                    draw.text((self.MARGEN, y), rec_text, fill="gray", font=font_small)
                    y += 14

            if vuelto > 0:
                linea_vuelto = "  Vuelto"
                monto_vuelto = f"S/ {vuelto:.2f}"
                bbox_v = draw.textbbox((0, 0), linea_vuelto, font=font_normal)
                bbox_mv = draw.textbbox((0, 0), monto_vuelto, font=font_normal)
                draw.text((self.MARGEN, y), linea_vuelto, fill="black", font=font_normal)
                draw.text(
                    (self.ANCHO - self.MARGEN_DERECHA - (bbox_mv[2] - bbox_mv[0]), y),
                    monto_vuelto, fill="black", font=font_normal,
                )
                y += 18

        y += 4
        y = linea_separadora(y)
        y += 4
        y = centrar("Gracias por su compra!", font_small, y, fill="gray")
        y = centrar("Comprobante interno", font_small, y, fill="gray")
        y = centrar("no es documento tributario", font_small, y, fill="gray")

        img = img.crop((0, 0, self.ANCHO, y + 10))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
