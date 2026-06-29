"""
Generador de Archivos Excel (.xlsx) estructurados y estilizados para InvoiceToSheet.
Utiliza pandas y openpyxl para crear hojas de cálculo con calidad contable profesional:
- Cabeceras corporativas estilizadas.
- Tipos de datos nativos (números reales, fechas).
- Formateo de moneda y totales automáticos con fórmulas.
- Anchos de columna calculados dinámicamente.
- Generación 100% en memoria mediante io.BytesIO para streaming inmediato.
"""

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from schemas import InvoiceData


def generate_invoice_excel(invoices: list[InvoiceData]) -> io.BytesIO:
    """
    Toma una lista de facturas extraídas (InvoiceData) y produce un buffer en memoria
    con un archivo Excel (.xlsx) diseñado profesionalmente.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Consolidado de Facturas"

    # Asegurar visualización de líneas de cuadrícula
    ws.views.sheetView[0].showGridLines = True

    # -------------------------------------------------------------
    # PALETA DE ESTILOS Y COLORES
    # -------------------------------------------------------------
    FONT_FAMILY = "Segoe UI"

    # Encabezado principal
    header_fill = PatternFill(
        start_color="1E293B", end_color="1E293B", fill_type="solid"
    )  # Slate oscuro
    header_font = Font(name=FONT_FAMILY, size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Filas de datos
    regular_font = Font(name=FONT_FAMILY, size=10, color="0F172A")
    regular_alignment_left = Alignment(horizontal="left", vertical="center")
    regular_alignment_center = Alignment(horizontal="center", vertical="center")
    regular_alignment_right = Alignment(horizontal="right", vertical="center")

    # Fila resumen / totales
    total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    total_font = Font(name=FONT_FAMILY, size=11, bold=True, color="0F172A")

    # Bordes sutiles
    thin_border_side = Side(border_style="thin", color="CBD5E1")
    data_border = Border(
        left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side
    )

    total_border = Border(
        top=Side(border_style="thin", color="0F172A"),
        bottom=Side(border_style="double", color="0F172A"),
    )

    # Fondos alternos (Zebra)
    row_even_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    row_odd_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    # -------------------------------------------------------------
    # DEFINICIÓN DE COLUMNAS
    # -------------------------------------------------------------
    columns = [
        ("N°", 6),
        ("Estado", 12),
        ("N° Factura", 18),
        ("Fecha Emisión", 16),
        ("Proveedor / Emisor", 32),
        ("ID Fiscal Emisor", 18),
        ("Cliente / Receptor", 28),
        ("Moneda", 10),
        ("Subtotal", 16),
        ("Impuestos", 16),
        ("Total", 16),
        ("Método Extracción", 18),
        ("Archivo Origen", 30),
    ]

    # Escribir Fila de Encabezados (Fila 1)
    ws.row_dimensions[1].height = 28
    for col_idx, (col_name, _) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = data_border

    # -------------------------------------------------------------
    # ESCRIBIR DATOS
    # -------------------------------------------------------------
    start_row = 2
    current_row = start_row

    for idx, inv in enumerate(invoices, start=1):
        ws.row_dimensions[current_row].height = 22
        fill = row_even_fill if current_row % 2 == 0 else row_odd_fill

        # Determinar etiqueta amigable del estado
        estado_label = (
            "Válido"
            if inv.estado == "success"
            else ("Revisar" if inv.estado == "warning" else "Error")
        )

        row_values = [
            (idx, regular_alignment_center, "@"),
            (estado_label, regular_alignment_center, "@"),
            (inv.numero_factura, regular_alignment_center, "@"),
            (inv.fecha_emision, regular_alignment_center, "YYYY-MM-DD"),
            (inv.nombre_proveedor, regular_alignment_left, "@"),
            (inv.id_fiscal_proveedor, regular_alignment_center, "@"),
            (inv.nombre_cliente or "No especificado", regular_alignment_left, "@"),
            (inv.moneda, regular_alignment_center, "@"),
            (float(inv.subtotal), regular_alignment_right, "#,##0.00"),
            (float(inv.impuestos), regular_alignment_right, "#,##0.00"),
            (float(inv.total), regular_alignment_right, "#,##0.00"),
            (inv.metodo_extraccion.upper(), regular_alignment_center, "@"),
            (inv.nombre_archivo_origen, regular_alignment_left, "@"),
        ]

        for col_idx, (val, alignment, num_format) in enumerate(row_values, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = regular_font
            cell.alignment = alignment
            cell.fill = fill
            cell.border = data_border
            cell.number_format = num_format

        current_row += 1

    # -------------------------------------------------------------
    # FILA DE TOTALES / RESUMEN (Fórmulas Excel reales)
    # -------------------------------------------------------------
    if invoices:
        ws.row_dimensions[current_row].height = 26
        # Celda de etiqueta "TOTALES GENERALES"
        label_cell = ws.cell(row=current_row, column=1, value="TOTALES")
        label_cell.font = total_font
        label_cell.alignment = regular_alignment_center
        label_cell.fill = total_fill
        label_cell.border = total_border

        # Rellenar celdas intermedias vacías con el estilo de total
        for col_idx in range(2, 9):
            c = ws.cell(row=current_row, column=col_idx, value="")
            c.fill = total_fill
            c.border = total_border

        # Columnas numéricas con fórmulas SUM: Subtotal (9), Impuestos (10), Total (11)
        for col_idx in [9, 10, 11]:
            col_letter = get_column_letter(col_idx)
            formula = f"=SUM({col_letter}{start_row}:{col_letter}{current_row - 1})"
            cell = ws.cell(row=current_row, column=col_idx, value=formula)
            cell.font = total_font
            cell.alignment = regular_alignment_right
            cell.fill = total_fill
            cell.border = total_border
            cell.number_format = "#,##0.00"

        # Celdas finales
        for col_idx in [12, 13]:
            c = ws.cell(row=current_row, column=col_idx, value="")
            c.fill = total_fill
            c.border = total_border

    # -------------------------------------------------------------
    # AJUSTE AUTOMÁTICO DE ANCHO DE COLUMNAS
    # -------------------------------------------------------------
    for col_idx, (_, default_width) in enumerate(columns, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row in range(1, current_row + 1):
            cell_value = ws.cell(row=row, column=col_idx).value
            if cell_value is not None:
                str_val = str(cell_value)
                # Omitir fórmulas largas en el cálculo visual
                if not str_val.startswith("="):
                    max_len = max(max_len, len(str_val))
        # Aplicar margen de holgura
        calculated_width = max(max_len + 4, default_width)
        ws.column_dimensions[col_letter].width = min(calculated_width, 50)

    # -------------------------------------------------------------
    # CONGELAR FILA DE ENCABEZADO
    # -------------------------------------------------------------
    ws.freeze_panes = "A2"

    # Guardar en memoria BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
