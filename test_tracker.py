import tempfile
import unittest
from pathlib import Path
from tracker_db import seed_realistic_data, fetch_latest_signals


class TestPriceTrackerSQL(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_tracker.db"
        seed_realistic_data(self.db_path, days=40)

    def tearDown(self):
        self.tmp.cleanup()

    def test_window_function_signals(self):
        signals = {row["sku"]: row for row in fetch_latest_signals(self.db_path)}

        # Sony XM5 & Samsung SSD should be flagged as GENUINE_ALL_TIME_LOW
        self.assertEqual(signals["AUD-XM5"]["price_signal"], "GENUINE_ALL_TIME_LOW")
        self.assertEqual(signals["SSD-SAM2"]["price_signal"], "GENUINE_ALL_TIME_LOW")

        # MacBook Air & LG Monitor had inflated MRPs on sale day -> FAKE_DISCOUNT_MRP_INFLATED
        self.assertEqual(signals["LAP-M3A"]["price_signal"], "FAKE_DISCOUNT_MRP_INFLATED")
        self.assertEqual(signals["MON-LG27"]["price_signal"], "FAKE_DISCOUNT_MRP_INFLATED")


if __name__ == "__main__":
    unittest.main()

