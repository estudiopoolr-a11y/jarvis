import unittest

from modules.nlp.text import normalizar_texto


class TestNormalizarTexto(unittest.TestCase):
    def test_quita_acentos_y_normaliza_espacios(self):
        self.assertEqual(normalizar_texto("  CÁfé   CON Leche "), "cafe con leche")

    def test_texto_vacio(self):
        self.assertEqual(normalizar_texto(""), "")


if __name__ == "__main__":
    unittest.main()
