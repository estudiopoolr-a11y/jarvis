import unittest
from unittest.mock import patch, MagicMock
from modules.ai import analizar_intencion_mensaje
from modules.intent_handler import ejecutar_intencion_nlp
import asyncio

class TestNLPTelegram(unittest.TestCase):
    def test_analizar_prestamo(self):
        texto = "Le presté 50k a Carlos"
        resultado = analizar_intencion_mensaje(texto)
        self.assertEqual(resultado["intent"], "REGISTRAR_PRESTAMO")
        self.assertEqual(resultado["persona"].lower(), "carlos")
        self.assertEqual(resultado["monto"], 50000.0)

    def test_analizar_gasto(self):
        texto = "Gasté 20 mil en almuerzo con efectivo"
        resultado = analizar_intencion_mensaje(texto)
        self.assertEqual(resultado["intent"], "REGISTRAR_GASTO")
        self.assertEqual(resultado["monto"], 20000.0)

    def test_analizar_saldo(self):
        texto = "Ajustar saldo Nequi a 100k"
        resultado = analizar_intencion_mensaje(texto)
        self.assertEqual(resultado["intent"], "ACTUALIZAR_CUENTA_KEBO")
        self.assertEqual(resultado["cuenta"].lower(), "nequi")
        self.assertEqual(resultado["nuevo_saldo"], 100000.0)

    def test_analizar_general(self):
        texto = "¿Cómo estás JARVIS?"
        resultado = analizar_intencion_mensaje(texto)
        self.assertEqual(resultado["intent"], "CONVERSACION_GENERAL")

    @patch('modules.intent_handler.registrar_prestamo')
    def test_ejecutar_prestamo(self, mock_reg):
        mock_reg.return_value = "loan_123"
        intent_data = {"intent": "REGISTRAR_PRESTAMO", "persona": "Carlos", "monto": 50000.0, "tipo": "prestado"}
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        res = loop.run_until_complete(ejecutar_intencion_nlp(intent_data, "user123"))
        self.assertIn("Préstamo registrado", res)

if __name__ == "__main__":
    unittest.main()

