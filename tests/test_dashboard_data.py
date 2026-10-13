import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.main import app
from app.routes.dashboard_stats import api_finanzas_resumen
from app.routes.widgets import api_widget_dashboard, obtener_resumen_widget
from modules.finance.dashboard import obtener_resumen_dashboard


class FakeDocument:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = data

    def to_dict(self):
        return self._data


class FakeDocumentReference:
    def __init__(self, db, path):
        self.db = db
        self.path = path

    def collection(self, name):
        return FakeCollection(self.db, self.path + (name,))


class FakeCollection:
    def __init__(self, db, path):
        self.db = db
        self.path = path

    def document(self, document_id):
        return FakeDocumentReference(self.db, self.path + (document_id,))

    def stream(self):
        return [
            FakeDocument(document_id, data)
            for document_id, data in self.db.documents.get(self.path, [])
        ]


class FakeFirestore:
    def __init__(self, documents):
        self.documents = documents

    def collection(self, name):
        return FakeCollection(self, (name,))


class TestDashboardData(unittest.TestCase):
    def setUp(self):
        self.db = FakeFirestore({
            ("categories",): [
                ("food", {"name": "Comida", "budget": 800}),
            ],
            ("transactions", "2026-10", "items"): [
                ("income-1", {"type": "income", "amount": 5000}),
                ("expense-1", {
                    "type": "expense",
                    "amount": 1250,
                    "category_id": "food",
                }),
                ("expense-2", {
                    "tipo": "gasto",
                    "monto": 250,
                    "category_name": "Transporte",
                }),
            ],
            ("budgets", "2026-10", "items"): [
                ("food-budget", {
                    "category_name": "Comida",
                    "amount": 2000,
                }),
                ("transport-budget", {
                    "categoria": "Transporte",
                    "limite": 1000,
                }),
            ],
            ("accounts",): [
                ("nu", {"nombre": "Nu", "balance": 7000}),
                ("cash", {"name": "Efectivo", "saldo": 500}),
            ],
        })

    def test_uses_current_month_transactions_budgets_and_account_balances(self):
        with patch("modules.finance.dashboard.get_db", return_value=self.db):
            result = obtener_resumen_dashboard("default", "2026-10")

        self.assertEqual(result["mes"], "Octubre 2026")
        self.assertEqual(result["ingresos"], 5000)
        self.assertEqual(result["gastos_mes"], 1500)
        self.assertEqual(result["balance"], 3500)
        self.assertEqual(result["balance_total"], 7500)
        self.assertEqual(result["presupuesto_mes"], 3000)
        self.assertEqual(result["porcentaje_usado"], 50)
        self.assertEqual(result["porcentaje"], 50)
        self.assertEqual(result["gastos_por_categoria"], {
            "Comida": 1250,
            "Transporte": 250,
        })
        self.assertEqual(len(result["cuentas"]), 2)

    def test_uses_category_budgets_when_no_month_budgets_exist(self):
        self.db.documents[("budgets", "2026-10", "items")] = []

        with patch("modules.finance.dashboard.get_db", return_value=self.db):
            result = obtener_resumen_dashboard("default", "2026-10")

        self.assertEqual(result["presupuesto_mes"], 800)

    def test_unavailable_firebase_is_not_returned_as_successful_zero_data(self):
        with patch("modules.finance.dashboard.get_db", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Firestore"):
                obtener_resumen_dashboard("default", "2026-10")

    def test_dashboard_and_widget_endpoints_are_registered_and_share_the_data(self):
        routes = {route.path for route in app.routes}
        self.assertIn("/api/finanzas/resumen", routes)
        self.assertIn("/api/widget/dashboard", routes)
        self.assertIn("/api/widget/resumen", routes)
        self.assertIn("/dashboard", routes)
        self.assertIn("/dashboard/v1", routes)

        expected = {"status": "ok", "total_gastos": 1250}
        with (
            patch(
                "app.routes.dashboard_stats.obtener_resumen_dashboard",
                return_value=expected,
            ) as obtener_api,
            patch(
                "app.routes.widgets.obtener_resumen_dashboard",
                return_value=expected,
            ) as obtener_widget,
        ):
            self.assertEqual(api_finanzas_resumen("user-1"), expected)
            self.assertEqual(api_widget_dashboard("user-1"), expected)
            self.assertEqual(obtener_resumen_widget(), expected)

        obtener_api.assert_called_once_with("user-1")
        obtener_widget.assert_any_call("user-1")
        obtener_widget.assert_any_call("default")

    def test_api_errors_are_not_converted_to_successful_zero_values(self):
        with patch(
            "app.routes.dashboard_stats.obtener_resumen_dashboard",
            side_effect=RuntimeError("Firebase unavailable"),
        ):
            with self.assertRaises(HTTPException) as dashboard_error:
                api_finanzas_resumen("default")

        self.assertEqual(dashboard_error.exception.status_code, 500)

        with patch(
            "app.routes.widgets.obtener_resumen_dashboard",
            side_effect=RuntimeError("Firebase unavailable"),
        ):
            with self.assertRaises(HTTPException) as widget_error:
                api_widget_dashboard("default")

        self.assertEqual(widget_error.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
