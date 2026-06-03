"""
Tests unitarios para el módulo de normalización de texto.

Verifica que el normalizador maneje correctamente:
- Texto vacío y None-like
- Normalización Unicode (NFC)
- Eliminación de caracteres de control
- Colapso de whitespace
- Normalización de line endings
- Reducción de líneas vacías excesivas
"""

from src.ingestion.normalizer import normalize


class TestNormalize:
    """Suite de tests para la función normalize()."""

    def test_empty_string(self):
        """Texto vacío devuelve string vacío."""
        assert normalize("") == ""

    def test_whitespace_only(self):
        """Texto solo con espacios/tabs devuelve vacío."""
        assert normalize("   \t  \n  ") == ""

    def test_collapse_multiple_spaces(self):
        """Múltiples espacios se colapsan a uno solo."""
        result = normalize("Error  de   conexión")
        assert result == "Error de conexión"

    def test_normalize_unicode_nfc(self):
        """Caracteres unicode compuestos se normalizan a NFC."""
        # 'é' como e + combining acute vs 'é' como single char
        composed = "caf\u00e9"        # NFC: é como un solo codepoint
        decomposed = "cafe\u0301"     # NFD: e + combining accent
        assert normalize(composed) == normalize(decomposed)

    def test_remove_control_characters(self):
        """Caracteres de control (excepto newline/tab) se eliminan."""
        text_with_bom = "\ufeffHola mundo"  # BOM (no es Cc pero es invisible)
        text_with_null = "Error\x00 fatal"  # NULL char (Cc category)
        result = normalize(text_with_null)
        assert "\x00" not in result
        assert "Error" in result
        assert "fatal" in result

    def test_tabs_replaced_by_spaces(self):
        """Tabs se reemplazan por espacios."""
        result = normalize("columna1\tcolumna2\tcolumna3")
        assert "\t" not in result
        assert "columna1" in result
        assert "columna2" in result

    def test_windows_line_endings(self):
        """Line endings de Windows (\\r\\n) se normalizan a \\n."""
        result = normalize("línea1\r\nlínea2\r\nlínea3")
        assert "\r" not in result
        assert "línea1\nlínea2\nlínea3" == result

    def test_reduce_excessive_blank_lines(self):
        """3+ líneas vacías consecutivas se reducen a máximo 2."""
        text = "Sección 1\n\n\n\n\nSección 2"
        result = normalize(text)
        assert "\n\n\n" not in result
        assert "Sección 1\n\nSección 2" == result

    def test_strip_leading_trailing_whitespace(self):
        """Espacios al inicio y final de líneas y del texto global se eliminan."""
        text = "  Error de conexión  \n  Verificar red  "
        result = normalize(text)
        lines = result.split("\n")
        for line in lines:
            assert line == line.strip()

    def test_preserves_meaningful_content(self):
        """La normalización no pierde contenido significativo."""
        original = (
            "3.2 Error: no se puede conectar con la base de datos\n"
            "Mensaje mostrado\n"
            "Error de conexión con el servidor de datos."
        )
        result = normalize(original)
        assert "3.2 Error" in result
        assert "base de datos" in result
        assert "Error de conexión" in result

    def test_real_document_normalizes_cleanly(self):
        """Un texto realista se normaliza sin perder estructura."""
        text = (
            "3.2 Error: no se puede conectar\r\n"
            "Mensaje mostrado\r\n"
            "\r\n"
            "Error de conexión con el servidor.\r\n"
            "\r\n"
            "Causas posibles\r\n"
            "Servidor apagado.\r\n"
            "Puerto bloqueado.\r\n"
        )
        result = normalize(text)
        assert "\r" not in result
        assert "3.2 Error" in result
        assert "Causas posibles" in result
        assert "Servidor apagado." in result
