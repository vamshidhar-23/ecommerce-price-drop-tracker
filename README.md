# E-Commerce Price Drop & Fake-Discount Tracker (Python + SQL)

A relational price intelligence engine that tracks daily product pricing in SQLite/PostgreSQL and uses **SQL Window Functions (`LAG`, `AVG`, `MIN`)** to distinguish genuine all-time-low drops from fake festive discounts (where retailers hike the listed MRP right before a sale).

## Key SQL Architecture (`schema.sql`)
* **Normalized Schema:** `products` (SKU, target price, category, retailer) + `price_history` (daily selling price & listed MRP with composite index `idx_price_history_prod_date`).
* **Window Function Analytics View (`vw_price_analytics`):**
  * `LAG(selling_price, 1) OVER (PARTITION BY product_id ORDER BY recorded_date)` for day-over-day price deltas.
  * `AVG(selling_price) OVER (... ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING)` for the rolling 30-day baseline price.
  * `MIN(selling_price) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)` to verify true historical lows.
* **Automated Signal Classification:**
  * `FAKE_DISCOUNT_MRP_INFLATED`: Retailer claims $\ge 25\%$ off MRP, but current selling price is within $3\%$ of the rolling 30-day average.
  * `GENUINE_ALL_TIME_LOW`: Strictly below all historical observations and $\ge 8\%$ below the 30-day rolling average.

## Quick Start
```bash
# Seed 45 days of historical data and display the live SQL analytical scorecard
python price_cli.py --seed

# Run unit tests
python -m unittest test_tracker.py
```

