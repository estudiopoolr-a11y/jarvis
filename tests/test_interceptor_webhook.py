import unittest
from unittest.mock import AsyncMock, patch

from app.routes.telegram import atender_telegram_webhook


class FakeRequest:
    def __init__(self, text="test"):
        self.text = text

    async def json(self):
        return {
            "message": {
                "chat": {"id": 123},
                "text": self.text,
            }
        }


class TestInterceptorEnWebhook(unittest.IsolatedAsyncioTestCase):
    """Probar que el interceptor financiero se ejecuta antes del LLM."""

    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.detectar_e_interactuar_finanzas")
    async def test_presupuesto_interceptado_antes_de_gemini(
        self, mock_interceptor, mock_despacho
    ):
        # El interceptor devuelve una respuesta con datos reales
        mock_interceptor.return_value = "Datos reales de Firestore"

        resultado = await atender_telegram_webhook(FakeRequest("presupuesto de julio"))

        self.assertEqual(resultado, {"status": "ok"})
        # Debe haber despachado la respuesta del interceptor
        mock_despacho.assert_awaited_once_with(123, "Datos reales de Firestore")
        # El interceptor debió ser llamado
        mock_interceptor.assert_called_once_with("presupuesto de julio")

    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.detectar_e_interactuar_finanzas")
    async def test_categoria_interceptada_antes_de_gemini(
        self, mock_interceptor, mock_despacho
    ):
        mock_interceptor.return_value = "Lista de categorias"

        resultado = await atender_telegram_webhook(FakeRequest("cuales son mis categorias"))

        self.assertEqual(resultado, {"status": "ok"})
        mock_despacho.assert_awaited_once_with(123, "Lista de categorias")

    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.detectar_e_interactuar_finanzas", return_value=None)
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value="Respuesta NLP")
    async def test_mensaje_no_financiero_pasa_a_llm(
        self, mock_router, mock_analizador, mock_interceptor, mock_despacho
    ):
        # Para mensajes no financieros, el interceptor retorna None
        mock_interceptor.return_value = None
        mock_analizador.return_value = {
            "intencion": "CONSULTA_GENERAL",
            "parametros": {"query": "hello"},
        }

        resultado = await atender_telegram_webhook(FakeRequest("hello"))

        self.assertEqual(resultado, {"status": "ok"})
        # Debe haber pasado al router NLP
        mock_router.assert_called_once_with("hello", "default")


if __name__ == "__main__":
    unittest.main()
