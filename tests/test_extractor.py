"""
Pruebas exhaustivas para el módulo de extracción y normalización.
"""

import os

import pytest

from extractor import RegexExtractor, extract_invoice_from_pdf, normalize_amount, normalize_date


class TestNormalizers:
    """Pruebas de normalización matemática y temporal."""

    @pytest.mark.parametrize(
        "raw_input,expected",
        [
            ("1,234.50", 1234.50),
            ("$ 1,234.50", 1234.50),
            ("1.234,50 €", 1234.50),
            ("1234,50", 1234.50),
            ("1234.50", 1234.50),
            ("150.00", 150.00),
            ("0.00", 0.00),
            ("", 0.00),
            (None, 0.00),
            ("abc", 0.00),
            ("10,000", 10000.00),
            ("150.000", 150000.00),
            ("1.500.000", 1500000.00),
            ("CLP $ 850.000", 850000.00),
        ],
    )
    def test_normalize_amount(self, raw_input, expected):
        assert normalize_amount(raw_input) == expected

    @pytest.mark.parametrize(
        "raw_input,expected",
        [
            ("15/01/2024", "2024-01-15"),
            ("2024-05-20", "2024-05-20"),
            ("15 de enero de 2024", "2024-01-15"),
            ("22 de Octubre del 2023", "2023-10-22"),
            ("10 de Febrero de 2025", "2025-02-10"),
            ("None", "None"),
            (None, "No identificada"),
            ("", "No identificada"),
        ],
    )
    def test_normalize_date(self, raw_input, expected):
        assert normalize_date(raw_input) == expected


class TestRegexExtractor:
    """Pruebas para el motor de expresiones regulares y reconciliación contable."""

    def test_mexican_invoice_extraction(self):
        text = """
        CORPORATIVO INDUSTRIAL S.A. DE C.V.
        RFC: CIN980101ABC
        FACTURA: F-2024-8891
        Fecha de Emisión: 10 de Mayo de 2024
        Cliente: EMPRESA CLIENTE
        Subtotal: $ 2,000.00
        IVA 16%: $ 320.00
        TOTAL: $ 2,320.00 MXN
        """
        result = RegexExtractor.extract(text, "mexico.pdf")
        assert result.numero_factura == "F-2024-8891"
        assert result.fecha_emision == "2024-05-10"
        assert result.id_fiscal_proveedor == "CIN980101ABC"
        assert result.subtotal == 2000.00
        assert result.impuestos == 320.00
        assert result.total == 2320.00
        assert result.moneda == "MXN"
        assert result.estado == "success"

    def test_spanish_invoice_extraction(self):
        text = """
        SERVICIOS MADRID S.L.
        NIF: B-87654321
        FACTURA N°: FAC-9021
        Fecha: 14/06/2024
        Base Imponible: 1.000,00
        IVA 21%: 210,00
        TOTAL A PAGAR: 1.210,00 EUR
        """
        result = RegexExtractor.extract(text, "espana.pdf")
        assert result.numero_factura == "FAC-9021"
        assert result.id_fiscal_proveedor == "B-87654321"
        assert result.subtotal == 1000.00
        assert result.impuestos == 210.00
        assert result.total == 1210.00
        assert result.moneda == "EUR"
        assert result.estado == "success"

    def test_reconciliation_calculates_missing_tax(self):
        """Si falta el impuesto explícito pero hay Subtotal y Total, calcula impuestos = Total - Subtotal."""
        text = """
        EMPRESA TEST
        FACTURA: F-100
        SUBTOTAL: 500.00
        TOTAL: 600.00
        """
        result = RegexExtractor.extract(text, "test.pdf")
        assert result.subtotal == 500.00
        assert result.total == 600.00
        assert result.impuestos == 100.00

    def test_warning_state_when_critical_fields_missing(self):
        """Si no se detecta total o número, marca estado 'warning'."""
        text = "Texto genérico sin importes ni números de comprobante."
        result = RegexExtractor.extract(text, "invalido.pdf")
        assert result.estado == "warning"
        assert result.mensaje_error is not None


class TestPdfPipeline:
    """Pruebas del pipeline completo de lectura en memoria y control de errores."""

    def test_empty_bytes_handling(self):
        result = extract_invoice_from_pdf(b"", "vacio.pdf")
        assert result.estado == "error"
        assert "vacío" in result.mensaje_error.lower()

    def test_corrupted_pdf_bytes_handling(self):
        result = extract_invoice_from_pdf(b"esto no es un pdf valido", "corrupto.pdf")
        assert result.estado == "error"
        assert "no se pudo extraer texto" in result.mensaje_error.lower()

    def test_sample_files_if_exist(self):
        sample_path = os.path.join(
            os.path.dirname(__file__), "..", "facturas_ejemplo", "factura_tech_solutions.pdf"
        )
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                res = extract_invoice_from_pdf(f.read(), "factura_tech_solutions.pdf")
                assert res.estado == "success"
                assert res.total > 0
