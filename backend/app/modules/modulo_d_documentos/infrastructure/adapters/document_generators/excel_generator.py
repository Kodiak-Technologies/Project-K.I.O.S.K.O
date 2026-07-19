from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

from app.modules.modulo_d_documentos.domain.ports.reporte_generator_port import ReporteGeneratorPort


class ExcelGenerator(ReporteGeneratorPort):
    async def generar_excel(self, datos: dict, nombre: str) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte"

        header_font = Font(bold=True, size=14)
        title_font = Font(bold=True, size=12)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font_white = Font(bold=True, color="FFFFFF", size=11)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        ws.merge_cells("A1:F1")
        ws["A1"] = datos.get("titulo", "Reporte")
        ws["A1"].font = header_font
        ws["A1"].alignment = Alignment(horizontal="center")

        ws["A2"] = f"Periodo: {datos.get('periodo', '')}"
        ws["A2"].font = title_font

        if "total_vendido" in datos:
            ws["A4"] = "Resumen"
            ws["A4"].font = title_font
            ws["A5"] = "Total Vendido:"
            ws["B5"] = datos.get("total_vendido", 0)
            ws["A6"] = "Número de Ventas:"
            ws["B6"] = datos.get("numero_ventas", 0)
            ws["A7"] = "Ticket Promedio:"
            ws["B7"] = datos.get("ticket_promedio", 0)

            top_productos = datos.get("top_productos", [])
            if top_productos:
                ws["A9"] = "Top Productos"
                ws["A9"].font = title_font

                headers = ["Producto", "Cantidad", "Total"]
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=10, column=col, value=header)
                    cell.font = header_font_white
                    cell.fill = header_fill
                    cell.border = thin_border

                for row, prod in enumerate(top_productos, 11):
                    ws.cell(row=row, column=1, value=prod.get("nombre", "")).border = thin_border
                    ws.cell(row=row, column=2, value=prod.get("cantidad", 0)).border = thin_border
                    ws.cell(row=row, column=3, value=prod.get("total", 0)).border = thin_border

        elif "productos" in datos:
            productos = datos.get("productos", [])
            if productos:
                ws["A4"] = "Productos Más Vendidos"
                ws["A4"].font = title_font

                headers = ["Producto", "Cantidad", "Total"]
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=5, column=col, value=header)
                    cell.font = header_font_white
                    cell.fill = header_fill
                    cell.border = thin_border

                for row, prod in enumerate(productos, 6):
                    ws.cell(row=row, column=1, value=prod.get("nombre", "")).border = thin_border
                    ws.cell(row=row, column=2, value=prod.get("cantidad", 0)).border = thin_border
                    ws.cell(row=row, column=3, value=prod.get("total", 0)).border = thin_border

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 15

        import io
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
