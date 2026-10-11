import unittest
import asyncio
from modules.ai import analizar_intencion_mensaje
from modules.intent_handler import ejecutar_intencion_nlp
from modules.nlp.router import procesar_intencion_natural


class TestNlpFirebaseIntegration(unittest.TestCase):
    """Integration tests for NLP analyzer with real Firebase data."""

    def test_analisis_intencion_presupuesto(self):
        """Prueba unitaria para el análisis de intención de presupuesto."""
        texto = "cual es el presupuesto de julio"
        resultado = analizar_intencion_mensaje(texto)
        self.assertIsInstance(resultado, dict)
        # The result uses "intent" (without accent) as the key
        self.assertIn("intent", resultado)
        print(f"Test NLP Intención Result: {resultado}", flush=True)

    def test_ejecucion_nlp_dinamica(self):
        """Prueba unitaria para la ejecución de intenciones NLP."""
        intent_mock = {
            "intent": "CONSULTAR_PRESUPUESTO",
            "parametros": {
                "mes": "julio",
                "query": "cual es el presupuesto de julio",
            },
        }
        # ejecutar_intencion_nlp is async, need to run it
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        respuesta = loop.run_until_complete(ejecutar_intencion_nlp(intent_mock))
        self.assertIsInstance(respuesta, str)
        self.assertTrue(len(respuesta) > 0)
        print(f"Test Ejecución NLP Response: {respuesta}", flush=True)


class TestNlpRouterIntegration(unittest.TestCase):
    """Tests for the deterministic NLP router with real Firebase data."""

    def test_router_q_cuenta_tengo(self):
        """Test that 'q cuenta tengo' is handled by the deterministic router."""
        texto = "q cuenta tengo"
        resultado = procesar_intencion_natural(texto, "default")
        # Should not return None - should be handled by router
        self.assertIsNotNone(resultado, 
            f"Router returned None for '{texto}' - should be handled by deterministic router")

    def test_router_mi_balance(self):
        """Test that 'mi balance' is handled by the deterministic router."""
        texto = "mi balance"
        resultado = procesar_intencion_natural(texto, "default")
        # Should not return None - should be handled by router
        self.assertIsNotNone(resultado,
            f"Router returned None for '{texto}' - should be handled by deterministic router")

    def test_router_presupuesto_julio(self):
        """Test that 'presupuesto de julio' is handled by the deterministic router."""
        texto = "presupuesto de julio"
        resultado = procesar_intencion_natural(texto, "default")
        self.assertIsNotNone(resultado,
            f"Router returned None for '{texto}'")


if __name__ == "__main__":
    unittest.main()