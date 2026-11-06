-- Schema for E-Commerce Price Drop & Fake-Discount Tracker

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    retailer TEXT NOT NULL,
    target_price REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    recorded_date TEXT NOT NULL,
    selling_price REAL NOT NULL,
    listed_mrp REAL NOT NULL,
    in_stock INTEGER DEFAULT 1,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    UNIQUE (product_id, recorded_date)
);

CREATE INDEX IF NOT EXISTS idx_price_history_prod_date 
ON price_history (product_id, recorded_date);

-- Analytical SQL View using Window Functions (LAG, AVG, MIN)
-- Compares today's selling price & MRP against prior day and rolling 30-day baselines.
CREATE VIEW IF NOT EXISTS vw_price_analytics AS
WITH windowed_prices AS (
    SELECT
        p.product_id,
        p.sku,
        p.name,
        p.category,
        p.retailer,
        p.target_price,
        ph.recorded_date,
        ph.selling_price,
        ph.listed_mrp,
        LAG(ph.selling_price, 1) OVER (
            PARTITION BY p.product_id ORDER BY ph.recorded_date
        ) AS prev_day_price,
        LAG(ph.listed_mrp, 1) OVER (
            PARTITION BY p.product_id ORDER BY ph.recorded_date
        ) AS prev_day_mrp,
        ROUND(AVG(ph.selling_price) OVER (
            PARTITION BY p.product_id
            ORDER BY ph.recorded_date
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ), 2) AS rolling_30d_avg_price,
        MIN(ph.selling_price) OVER (
            PARTITION BY p.product_id
            ORDER BY ph.recorded_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS historical_low_price
    FROM price_history ph
    JOIN products p ON p.product_id = ph.product_id
)
SELECT
    *,
    ROUND((listed_mrp - selling_price) * 100.0 / listed_mrp, 1) AS advertised_discount_pct,
    ROUND(
        CASE 
            WHEN rolling_30d_avg_price IS NOT NULL AND rolling_30d_avg_price > 0
            THEN (rolling_30d_avg_price - selling_price) * 100.0 / rolling_30d_avg_price
            ELSE 0.0
        END, 1
    ) AS real_vs_30d_avg_pct,
    CASE
        -- Fake Discount: Retailer inflates MRP or claims >=25% off, but price is within 3% of (or above) 30d average
        WHEN rolling_30d_avg_price IS NOT NULL
             AND ((listed_mrp - selling_price) * 100.0 / listed_mrp) >= 25.0
             AND selling_price >= (rolling_30d_avg_price * 0.97)
        THEN 'FAKE_DISCOUNT_MRP_INFLATED'

        -- All-Time Low: Strictly lower than any previous day and at least 8% below 30d avg
        WHEN historical_low_price IS NOT NULL
             AND selling_price < historical_low_price
             AND selling_price <= (rolling_30d_avg_price * 0.92)
        THEN 'GENUINE_ALL_TIME_LOW'

        -- Target Hit: Below user's desired target price
        WHEN selling_price <= target_price
        THEN 'TARGET_PRICE_HIT'

        ELSE 'NORMAL_FLUCTUATION'
    END AS price_signal
FROM windowed_prices;

