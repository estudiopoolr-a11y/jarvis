import json
import unittest
from unittest.mock import patch

from modules.ai import analizar_solicitud_consciente


class TestAnalizarSolicitudConsciente(unittest.IsolatedAsyncioTestCase):
    @patch("modules.gemini.client.genai", new=object())
    @patch(
        "modules.gemini.client._gemini_call_with_fallback",
        return_value=json.dumps(
            {
                "intencion": "CONSULTAR_FINANZAS",
                "parametros": {"mes": "agosto", "query": "resumen de presupuesto"},
            },
        ),
    )
    async def test_extrae_intencion_y_parametros(self, _mock_gemini):
        resultado = await analizar_solicitud_consciente(
            "resumen de presupuesto de agosto",
            historial=["¿Cómo va mi presupuesto?"],
        )

        self.assertEqual(resultado["intencion"], "CONSULTAR_FINANZAS")
        self.assertEqual(resultado["parametros"]["mes"], "agosto")

    @patch("modules.gemini.client._gemini_call_with_fallback")
    async def test_consulta_vacia_no_llama_a_gemini(self, mock_gemini):
        resultado = await analizar_solicitud_consciente("  ")

        self.assertEqual(resultado, {"intencion": "DESCONOCIDO", "parametros": {}})
        mock_gemini.assert_not_called()

    @patch("modules.gemini.client.genai", new=object())
    @patch(
        "modules.gemini.client._gemini_call_with_fallback",
        return_value="esto no es JSON",
    )
    async def test_respuesta_no_json_se_informa(self, _mock_gemini):
        with self.assertRaisesRegex(ValueError, "JSON inválido"):
            await analizar_solicitud_consciente("presupuesto de agosto")


if __name__ == "__main__":
    unittest.main()
