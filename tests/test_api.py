import sys
import os
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app, startup_event

class TestSupplyChainAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        startup_event()
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "healthy")

    def test_get_dashboard_kpis(self):
        resp = self.client.get("/inventory/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_products", data)
        self.assertIn("total_inventory_value", data)
        self.assertGreater(data["total_products"], 0)

    def test_get_exceptions(self):
        resp = self.client.get("/exceptions")
        self.assertEqual(resp.status_code, 200)
        exceptions = resp.json()
        self.assertIsInstance(exceptions, list)
        self.assertGreater(len(exceptions), 0)

    def test_get_supplier_comparison(self):
        resp = self.client.get("/suppliers/compare")
        self.assertEqual(resp.status_code, 200)
        suppliers = resp.json()
        self.assertIsInstance(suppliers, list)
        self.assertGreater(len(suppliers), 0)

    def test_get_forecast(self):
        resp = self.client.get("/analytics/forecast")
        self.assertEqual(resp.status_code, 200)
        forecasts = resp.json()
        self.assertIsInstance(forecasts, list)
        self.assertGreater(len(forecasts), 0)

    def test_post_supply_query(self):
        resp = self.client.post("/supply/query", json={
            "query": "Which products are likely to face stock shortages in the next seven days and why?"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("recommended_actions", data)

    def test_post_analytics_run(self):
        resp = self.client.post("/analytics/run")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

if __name__ == '__main__':
    unittest.main()
