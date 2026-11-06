import argparse
from tracker_db import (
    DB_DEFAULT,
    seed_realistic_data,
    fetch_latest_signals,
    fetch_competitor_summary,
)


def print_dashboard(signals, retailers):
    print("\n" + "=" * 96)
    print("  E-COMMERCE PRICE DROP & FAKE-DISCOUNT TRACKER (SQL WINDOW FUNCTION ENGINE)")
    print("=" * 96)
    header = (
        f"  {'SKU':<9} | {'PRODUCT':<30} | {'CURR PRICE':>10} | "
        f"{'30D AVG':>10} | {'CLAIMED':>8} | {'TRUE DIFF':>9} | {'SIGNAL'}"
    )
    print(header)
    print("-" * 96)

    for row in signals:
        prod_short = row["name"][:29]
        curr = f"Rs.{row['selling_price']:,.0f}"
        avg30 = f"Rs.{row['rolling_30d_avg_price']:,.0f}"
        claimed = f"-{row['advertised_discount_pct']:.1f}%"
        true_diff = f"{-row['real_vs_30d_avg_pct']:+.1f}%"
        print(
            f"  {row['sku']:<9} | {prod_short:<30} | {curr:>10} | "
            f"{avg30:>10} | {claimed:>8} | {true_diff:>9} | {row['price_signal']}"
        )

    print("=" * 96)
    print("\n  RETAILER DISCOUNT CREDIBILITY SCORECARD:")
    print("-" * 74)
    print(f"  {'RETAILER':<16} | {'ITEMS':>5} | {'CLAIMED OFF':>13} | {'REAL SAVINGS':>13} | {'FAKE FLAGS'}")
    print("-" * 74)
    for r in retailers:
        print(
            f"  {r['retailer']:<16} | {r['tracked_products']:>5} | "
            f"{r['avg_claimed_discount_pct']:>12.1f}% | "
            f"{r['avg_true_savings_vs_30d_pct']:>12.1f}% | "
            f"{r['fake_sale_flags']:>10}"
        )
    print("-" * 74 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="E-Commerce Price Drop & Fake-Discount SQL Tracker"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Initialize SQLite database and populate 45 days of historical pricing"
    )
    args = parser.parse_args()

    if args.seed or not DB_DEFAULT.exists():
        print("[+] Initializing SQL schema and seeding 45 days of price history...")
        seed_realistic_data(DB_DEFAULT)

    signals = fetch_latest_signals(DB_DEFAULT)
    retailers = fetch_competitor_summary(DB_DEFAULT)
    print_dashboard(signals, retailers)


if __name__ == "__main__":
    main()

