import sqlite3
import random
from contextlib import closing
from pathlib import Path
from datetime import date, timedelta

DB_DEFAULT = Path(__file__).parent / "price_tracker.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path=DB_DEFAULT):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_DEFAULT):
    with closing(get_connection(db_path)) as conn:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()


def seed_realistic_data(db_path=DB_DEFAULT, days=45):
    """
    Populates 6 products across 45 days of history with realistic pricing behavior:
    - Some products have genuine price drops on Day 45.
    - Some products inflate their MRP right before Day 45 ('Fake Sale' pattern).
    """
    random.seed(42)
    init_db(db_path)

    catalog = [
        # (sku, name, category, retailer, target_price, normal_price, normal_mrp, behavior)
        ("AUD-XM5", "Sony WH-1000XM5 Wireless Headphones", "Audio", "Amazon IN", 24990, 28990, 34990, "GENUINE_DROP"),
        ("LAP-M3A", "MacBook Air 13 M3 (16GB/512GB)", "Laptops", "Flipkart", 102000, 112900, 114900, "FAKE_DISCOUNT"),
        ("MON-LG27", "LG Ultragear 27-inch QHD 165Hz Monitor", "Monitors", "Amazon IN", 18500, 21500, 28000, "FAKE_DISCOUNT"),
        ("SSD-SAM2", "Samsung 990 PRO 2TB NVMe M.2 SSD", "Storage", "MDComputers", 14500, 16800, 22999, "GENUINE_DROP"),
        ("KEY-K2V2", "Keychron K2 Pro Mechanical Keyboard", "Peripherals", "Meckeys", 8200, 8999, 10999, "STABLE"),
        ("GPU-4060", "ASUS Dual RTX 4060 OC 8GB GDDR6", "Components", "PrimeABGB", 26500, 28500, 33000, "TARGET_HIT"),
    ]

    start_date = date(2025, 9, 15)

    with closing(get_connection(db_path)) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM price_history;")
        cur.execute("DELETE FROM products;")

        for sku, name, cat, retailer, target, base_price, base_mrp, behavior in catalog:
            cur.execute(
                """
                INSERT INTO products (sku, name, category, retailer, target_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sku, name, cat, retailer, target),
            )
            prod_id = cur.lastrowid

            for d in range(days):
                curr_date = (start_date + timedelta(days=d)).isoformat()
                # Small daily noise (+/- 1.5%)
                noise = random.uniform(-0.012, 0.012)
                selling = round((base_price * (1 + noise)) / 10) * 10
                mrp = base_mrp

                # Last day (Sale Event Day) special patterns
                if d == days - 1:
                    if behavior == "GENUINE_DROP":
                        # Real 18% discount below typical selling price
                        selling = round((base_price * 0.82) / 10) * 10
                    elif behavior == "FAKE_DISCOUNT":
                        # Keep selling price basically the same as 30-day average,
                        # but hike the listed MRP by 35% to advertise a huge "% OFF"!
                        selling = base_price
                        mrp = round((base_price * 1.48) / 100) * 100
                    elif behavior == "TARGET_HIT":
                        selling = target - 300

                cur.execute(
                    """
                    INSERT INTO price_history (product_id, recorded_date, selling_price, listed_mrp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (prod_id, curr_date, selling, mrp),
                )

        conn.commit()


def fetch_latest_signals(db_path=DB_DEFAULT):
    """Queries the SQL analytical view for the most recent date."""
    query = """
    SELECT
        sku,
        name,
        retailer,
        recorded_date,
        selling_price,
        listed_mrp,
        rolling_30d_avg_price,
        historical_low_price,
        advertised_discount_pct,
        real_vs_30d_avg_pct,
        price_signal
    FROM vw_price_analytics
    WHERE recorded_date = (SELECT MAX(recorded_date) FROM price_history)
    ORDER BY real_vs_30d_avg_pct DESC;
    """
    with closing(get_connection(db_path)) as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


def fetch_competitor_summary(db_path=DB_DEFAULT):
    """Aggregates average real vs advertised discounts by retailer using SQL CTEs."""
    query = """
    SELECT
        retailer,
        COUNT(DISTINCT sku) AS tracked_products,
        ROUND(AVG(advertised_discount_pct), 1) AS avg_claimed_discount_pct,
        ROUND(AVG(real_vs_30d_avg_pct), 1) AS avg_true_savings_vs_30d_pct,
        SUM(CASE WHEN price_signal = 'FAKE_DISCOUNT_MRP_INFLATED' THEN 1 ELSE 0 END) AS fake_sale_flags
    FROM vw_price_analytics
    WHERE recorded_date = (SELECT MAX(recorded_date) FROM price_history)
    GROUP BY retailer
    ORDER BY avg_true_savings_vs_30d_pct DESC;
    """
    with closing(get_connection(db_path)) as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]
