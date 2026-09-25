import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.api import app


class TestTelegramWebhook(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoints(self):
        resp_root = self.client.get("/")
        self.assertEqual(resp_root.status_code, 200)
        self.assertEqual(resp_root.json().get("status"), "ok")

        resp_health = self.client.get("/health")
        self.assertEqual(resp_health.status_code, 200)
        self.assertEqual(resp_health.json().get("status"), "ok")

    @patch("modules.ai.procesar_intencion_natural")
    @patch("httpx.AsyncClient.post")
    def test_webhook_telegram_success(self, mock_httpx_post, mock_nlp):
        mock_nlp.return_value = "Respuesta de prueba JARVIS"
        mock_httpx_post.return_value = AsyncMock(status_code=200, text="ok")

        payload = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {"id": 987654, "first_name": "TestUser"},
                "chat": {"id": 987654, "type": "private"},
                "text": "Hola JARVIS",
            },
        }

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:FAKE_TOKEN"}):
            resp = self.client.post("/webhook", json=payload)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
