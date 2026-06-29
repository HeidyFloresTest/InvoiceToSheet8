"""
Generador de facturas PDF de prueba sin dependencias externas.
Crea dos archivos PDF válidos con estructura de factura comercial para probar el sistema inmediatamente.
"""

import os


def create_simple_pdf(filename: str, lines: list):
    # Construir contenido del stream de texto PDF
    stream_content = "BT\n/F1 11 Tf\n50 720 Td\n18 TL\n"
    for line in lines:
        escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({escaped_line}) '\n"
    stream_content += "ET"

    stream_bytes = stream_content.encode("latin-1")
    stream_len = len(stream_bytes)

    objects = []
    # Obj 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # Obj 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # Obj 3: Page
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    # Obj 4: Stream
    objects.append(
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin-1")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    # Obj 5: Font
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    # Armar PDF con tabla xref
    header = b"%PDF-1.4\n"
    offsets = [0]
    body = b""
    current_offset = len(header)
    for obj in objects:
        offsets.append(current_offset)
        body += obj
        current_offset += len(obj)

    xref_offset = len(header) + len(body)
    xref = f"xref\n0 {len(offsets)}\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n"

    trailer = f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"

    with open(filename, "wb") as f:
        f.write(header + body + xref.encode("latin-1") + trailer.encode("latin-1"))


def generate_samples():
    output_dir = os.path.join(os.path.dirname(__file__), "facturas_ejemplo")
    os.makedirs(output_dir, exist_ok=True)

    # Factura 1 (México)
    lines_1 = [
        "TECH SOLUTIONS LATAM S.A. DE C.V.",
        "RFC: TSO120405ABC",
        "Av. Paseo de la Reforma 450, Ciudad de Mexico",
        "-------------------------------------------------------------",
        "FACTURA N: F-2024-8841",
        "Fecha de Emision: 15 de Marzo de 2024",
        "Moneda: MXN",
        "-------------------------------------------------------------",
        "Cliente: GRUPO INDUSTRIAL DEL NORTE",
        "RFC Cliente: GIN990203XYZ",
        "-------------------------------------------------------------",
        "Servicio de Consultoria Cloud      1.00     $ 2,500.00",
        "Soporte Tecnico Mensual           1.00     $ 1,000.00",
        "-------------------------------------------------------------",
        "SUBTOTAL: $ 3,500.00",
        "IVA (16%): $ 560.00",
        "TOTAL A PAGAR: $ 4,060.00 MXN",
    ]
    file_1 = os.path.join(output_dir, "factura_tech_solutions.pdf")
    create_simple_pdf(file_1, lines_1)

    # Factura 2 (España / Europa)
    lines_2 = [
        "INNOVACIONES DIGITALES IBERIA S.L.",
        "NIF: B-87654321",
        "Calle Gran Via 28, 28013 Madrid, Espana",
        "-------------------------------------------------------------",
        "FACTURA: FAC-2024-0092",
        "Fecha: 22 de Abril de 2024",
        "Moneda: EUR",
        "-------------------------------------------------------------",
        "Cliente: GLOBAL LOGISTICS EUROPE",
        "-------------------------------------------------------------",
        "Licencias de Software Anuales       3.00       1.200,00",
        "-------------------------------------------------------------",
        "Base Imponible: 1.200,00",
        "IVA (21%): 252,00",
        "TOTAL: 1.452,00 EUR",
    ]
    file_2 = os.path.join(output_dir, "factura_innovaciones_madrid.pdf")
    create_simple_pdf(file_2, lines_2)

    print(f"Facturas creadas exitosamente en: {output_dir}")


if __name__ == "__main__":
    generate_samples()
