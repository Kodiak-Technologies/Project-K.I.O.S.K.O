from PIL import Image, ImageDraw, ImageFont


class BoletaPngGenerator:
    ANCHO = 400
    MARGEN = 20

    async def generar(
        self,
        numero: str,
        total: float,
        fecha: str,
        productos: list[dict],
        nombre_negocio: str = "Mi Tienda",
    ) -> bytes:
        alto = 200 + len(productos) * 30
        img = Image.new("RGB", (self.ANCHO, alto), color="white")
        draw = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 18)
            font_normal = ImageFont.truetype("arial.ttf", 12)
        except OSError:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()

        y = self.MARGEN
        draw.text((self.MARGEN, y), nombre_negocio, fill="black", font=font_title)
        y += 30
        draw.text((self.MARGEN, y), f"Boleta: {numero}", fill="black", font=font_normal)
        y += 20
        draw.text((self.MARGEN, y), f"Fecha: {fecha}", fill="black", font=font_normal)
        y += 30

        draw.line([(self.MARGEN, y), (self.ANCHO - self.MARGEN, y)], fill="gray", width=1)
        y += 10

        for prod in productos:
            nombre = prod.get("nombre", "")
            cantidad = prod.get("cantidad", 0)
            precio = prod.get("precio_unitario", 0)
            subtotal = prod.get("subtotal", cantidad * precio)
            draw.text(
                (self.MARGEN, y),
                f"{nombre} x{cantidad} - S/ {subtotal:.2f}",
                fill="black",
                font=font_normal,
            )
            y += 25

        y += 10
        draw.line([(self.MARGEN, y), (self.ANCHO - self.MARGEN, y)], fill="gray", width=1)
        y += 10
        draw.text((self.MARGEN, y), f"TOTAL: S/ {total:.2f}", fill="black", font=font_title)

        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
