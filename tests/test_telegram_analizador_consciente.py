import unittest
from unittest.mock import AsyncMock, patch

from app.routes.telegram import atender_telegram_webhook


class FakeRequest:
    def __init__(self, text="¿Qué puedes hacer?"):
        self.text = text

    async def json(self):
        return {
            "message": {
                "chat": {"id": 123},
                "text": self.text,
            }
        }


class TestWebhookAnalizadorConsciente(unittest.IsolatedAsyncioTestCase):
    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value="Respuesta directa")
    async def test_router_deterministico_tiene_prioridad(
        self, router, analizador, despacho, _print
    ):
        resultado = await atender_telegram_webhook(FakeRequest())

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Qué puedes hacer?", "default")
        analizador.assert_not_awaited()
        despacho.assert_awaited_once_with(123, "Respuesta directa")

    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.pensar_respuesta", return_value="Respuesta Gemini")
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value=None)
    async def test_consulta_general_usa_respuesta_generativa(
        self, router, analizador, pensar, despacho, _print
    ):
        analizador.return_value = {
            "intencion": "CONSULTA_GENERAL",
            "parametros": {"query": "¿Qué puedes hacer?"},
        }

        resultado = await atender_telegram_webhook(FakeRequest())

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Qué puedes hacer?", "default")
        pensar.assert_called_once_with("¿Qué puedes hacer?")
        despacho.assert_awaited_once_with(123, "Respuesta Gemini")

    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch(
        "app.routes.telegram.ejecutar_intencion_nlp",
        new_callable=AsyncMock,
        return_value="Gasto registrado",
    )
    @patch(
        "app.routes.telegram.analizar_intencion_mensaje",
        return_value={"intent": "REGISTRAR_GASTO"},
    )
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value=None)
    async def test_finanzas_pasa_al_parser_detallado_existente(
        self, router, analizador, parser, ejecutar, despacho, _print
    ):
        analizador.return_value = {
            "intencion": "CONSULTAR_FINANZAS",
            "parametros": {"categoria": "comida"},
        }

        resultado = await atender_telegram_webhook(FakeRequest())

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Qué puedes hacer?", "default")
        parser.assert_called_once_with("¿Qué puedes hacer?")
        ejecutar.assert_awaited_once_with({"intent": "REGISTRAR_GASTO"})
        despacho.assert_awaited_once_with(123, "Gasto registrado")

    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.pensar_respuesta", return_value="Respuesta Gemini")
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value=None)
    async def test_tarea_no_reconocida_no_finge_ejecucion(
        self, router, analizador, pensar, despacho, _print
    ):
        analizador.return_value = {
            "intencion": "GESTIONAR_TAREAS",
            "parametros": {"query": "recuérdame algo"},
        }

        resultado = await atender_telegram_webhook(FakeRequest())

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Qué puedes hacer?", "default")
        analizador.assert_awaited_once_with("¿Qué puedes hacer?")
        pensar.assert_called_once_with("¿Qué puedes hacer?")
        despacho.assert_awaited_once_with(123, "Respuesta Gemini")

    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.pensar_respuesta", return_value="Respuesta Gemini")
    @patch(
        "app.routes.telegram.analizar_intencion_mensaje",
        return_value={"intent": "CONVERSACION_GENERAL"},
    )
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value=None)
    async def test_finanzas_no_cerradas_usan_respuesta_generativa(
        self, router, analizador, parser, pensar, despacho, _print
    ):
        analizador.return_value = {
            "intencion": "CONSULTAR_FINANZAS",
            "parametros": {"query": "¿Qué puedes hacer?"},
        }

        resultado = await atender_telegram_webhook(FakeRequest())

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Qué puedes hacer?", "default")
        parser.assert_called_once_with("¿Qué puedes hacer?")
        pensar.assert_called_once_with("¿Qué puedes hacer?")
        despacho.assert_awaited_once_with(123, "Respuesta Gemini")

    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.pensar_respuesta", return_value="Respuesta Gemini")
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value=None)
    async def test_intencion_desconocida_usa_respuesta_generativa(
        self, router, analizador, pensar, despacho, _print
    ):
        analizador.return_value = {"intencion": None, "parametros": {}}

        resultado = await atender_telegram_webhook(FakeRequest())

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Qué puedes hacer?", "default")
        pensar.assert_called_once_with("¿Qué puedes hacer?")
        despacho.assert_awaited_once_with(123, "Respuesta Gemini")

    @patch("builtins.print")
    @patch("app.routes.telegram.despachar_respuesta_telegram", new_callable=AsyncMock)
    @patch("app.routes.telegram.pensar_respuesta", return_value="4")
    @patch("app.routes.telegram.analizar_solicitud_consciente", new_callable=AsyncMock)
    @patch("app.routes.telegram.procesar_intencion_natural", return_value=None)
    async def test_consulta_aritmetica_usa_respuesta_generativa(
        self, router, analizador, pensar, despacho, _print
    ):
        analizador.return_value = {
            "intencion": "CONSULTA_GENERAL",
            "parametros": {"query": "¿Cuánto es 2 + 2?"},
        }

        resultado = await atender_telegram_webhook(FakeRequest("¿Cuánto es 2 + 2?"))

        self.assertEqual(resultado, {"status": "ok"})
        router.assert_called_once_with("¿Cuánto es 2 + 2?", "default")
        pensar.assert_called_once_with("¿Cuánto es 2 + 2?")
        despacho.assert_awaited_once_with(123, "4")


if __name__ == "__main__":
    unittest.main()
