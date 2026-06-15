"""
Script de pruebas unitarias y de integración para validar la lógica de InvoiceToSheet:
1. Normalización de montos y fechas.
2. Motor de reglas Regex con diferentes formatos de facturas.
3. Generación del archivo Excel en memoria.
"""

import io
import unittest
from schemas import InvoiceData
from extractor import normalize_amount, normalize_date, RegexExtractor
from excel_generator import generate_invoice_excel


class TestInvoiceToSheetPipeline(unittest.TestCase):

    def test_normalize_amount(self):
        """Verifica la normalización de distintos estándares numéricos."""
        self.assertEqual(normalize_amount("1,234.50"), 1234.50)
        self.assertEqual(normalize_amount("$ 1,234.50"), 1234.50)
        self.assertEqual(normalize_amount("1.234,50 €"), 1234.50)
        self.assertEqual(normalize_amount("1234,50"), 1234.50)
        self.assertEqual(normalize_amount("150.00"), 150.00)
        self.assertEqual(normalize_amount("0.00"), 0.00)
        self.assertEqual(normalize_amount(None), 0.00)

    def test_normalize_date(self):
        """Verifica la normalización de formatos de fecha a YYYY-MM-DD."""
        self.assertEqual(normalize_date("15/01/2024"), "2024-01-15")
        self.assertEqual(normalize_date("2024-05-20"), "2024-05-20")
        self.assertEqual(normalize_date("15 de enero de 2024"), "2024-01-15")
        self.assertEqual(normalize_date("22 de Octubre del 2023"), "2023-10-22")

    def test_regex_extractor_sample_invoice(self):
        """Simula el texto plano de una factura típica en español."""
        sample_text = """
        TECH SOLUTIONS S.A. DE C.V.
        RFC: TSO120405ABC
        Dirección: Av. Reforma 123, Ciudad de México

        FACTURA N°: F-2024-9981
        Fecha de Emisión: 18 de Marzo de 2024

        Cliente: INDUSTRIAS DEL NORTE S.A.
        RFC Cliente: INO980101XYZ

        Descripción               Cantidad   Precio Unitario    Importe
        Licencia de Software             1         1,000.00   1,000.00

        SUBTOTAL: $ 1,000.00
        IVA (16%): $ 160.00
        TOTAL A PAGAR: $ 1,160.00 MXN
        """
        invoice = RegexExtractor.extract(sample_text, "factura_tech_sample.pdf")

        self.assertEqual(invoice.numero_factura, "F-2024-9981")
        self.assertEqual(invoice.fecha_emision, "2024-03-18")
        self.assertEqual(invoice.id_fiscal_proveedor, "TSO120405ABC")
        self.assertIn("TECH SOLUTIONS", invoice.nombre_proveedor)
        self.assertEqual(invoice.subtotal, 1000.00)
        self.assertEqual(invoice.impuestos, 160.00)
        self.assertEqual(invoice.total, 1160.00)
        self.assertEqual(invoice.moneda, "MXN")
        self.assertEqual(invoice.estado, "success")

    def test_excel_generation(self):
        """Verifica que el generador de Excel produzca un buffer BytesIO válido sin errores."""
        invoices = [
            InvoiceData(
                numero_factura="FAC-001",
                fecha_emision="2024-01-10",
                nombre_proveedor="Empresa Alfa S.A.",
                id_fiscal_proveedor="B12345678",
                nombre_cliente="Cliente Beta",
                subtotal=500.00,
                impuestos=105.00,
                total=605.00,
                moneda="EUR",
                nombre_archivo_origen="alfa_001.pdf",
                estado="success"
            ),
            InvoiceData(
                numero_factura="FAC-002",
                fecha_emision="2024-01-12",
                nombre_proveedor="Proveedor Gamma Inc.",
                id_fiscal_proveedor="12-3456789",
                nombre_cliente="Cliente Beta",
                subtotal=1200.00,
                impuestos=0.00,
                total=1200.00,
                moneda="USD",
                nombre_archivo_origen="gamma_002.pdf",
                estado="warning"
            )
        ]

        excel_stream = generate_invoice_excel(invoices)
        self.assertIsInstance(excel_stream, io.BytesIO)
        content = excel_stream.getvalue()
        # Verificar la firma mágica del archivo zip/xlsx (PK\x03\x04)
        self.assertTrue(content.startswith(b"PK\x03\x04"))
        self.assertGreater(len(content), 2000)


if __name__ == "__main__":
    unittest.main()
