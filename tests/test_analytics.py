import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, get_connection
from backend.sample_data_loader import load_sample_datasets
from backend.analytics_engine import (
    run_deterministic_analytics,
    calculate_supplier_comparison,
    get_dashboard_kpis
)
from backend.ai_service import answer_natural_language_query, generate_exception_ai_insights

class TestSupplyChainAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        load_sample_datasets()

    def test_database_loaded(self):
        conn = get_connection()
        prod_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        supp_count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        ord_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        inv_count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        conn.close()
        
        self.assertGreater(prod_count, 0)
        self.assertGreater(supp_count, 0)
        self.assertGreater(ord_count, 0)
        self.assertGreater(inv_count, 0)

    def test_deterministic_analytics_execution(self):
        results = run_deterministic_analytics()
        exceptions = results['exceptions']
        self.assertIsInstance(exceptions, list)
        self.assertGreater(len(exceptions), 0)
        
        for exc in exceptions:
            self.assertIn('exception_id', exc)
            self.assertIn('exception_type', exc)
            self.assertIn('severity', exc)
            self.assertIn('deterministic_metrics', exc)
            self.assertIn(exc['severity'], ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'])

    def test_supplier_comparison(self):
        suppliers = calculate_supplier_comparison()
        self.assertIsInstance(suppliers, list)
        self.assertGreater(len(suppliers), 0)
        
        for s in suppliers:
            self.assertIn('otif_rate_pct', s)
            self.assertIn('reliability_score', s)
            self.assertIn('risk_tier', s)
            self.assertTrue(0.0 <= s['otif_rate_pct'] <= 100.0)
            self.assertTrue(0.0 <= s['reliability_score'] <= 100.0)

    def test_dashboard_kpis(self):
        kpis = get_dashboard_kpis()
        self.assertIn('total_products', kpis)
        self.assertIn('total_inventory_value', kpis)
        self.assertIn('average_otif_rate', kpis)
        self.assertGreater(kpis['total_inventory_value'], 0)

    def test_natural_language_querying(self):
        query = "Which products are likely to face stock shortages in the next seven days and why?"
        res = answer_natural_language_query(query)
        self.assertIn("answer", res)
        self.assertIn("recommended_actions", res)
        self.assertGreater(len(res["recommended_actions"]), 0)

if __name__ == '__main__':
    unittest.main()
