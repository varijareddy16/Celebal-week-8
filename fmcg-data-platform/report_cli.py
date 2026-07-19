"""
report_cli.py

command line reporting tool for the fmcg data warehouse.
this stands in for the power bi / databricks sql dashboard layer,
since those tools are not available for this project. every report
here queries the gold layer tables directly.

usage examples:

    python report_cli.py overview
    python report_cli.py monthly-revenue
    python report_cli.py category-performance
    python report_cli.py region-performance
    python report_cli.py company-comparison
    python report_cli.py payment-modes
    python report_cli.py top-products
    python report_cli.py top-products --limit 5

run "python report_cli.py --help" to see all available reports.
"""

import argparse
import sqlite3
import os
import sys

DB_PATH = "fmcg_warehouse.db"


def get_connection():
    if not os.path.exists(DB_PATH):
        print(f"error: warehouse file '{DB_PATH}' not found.")
        print("run scripts/build_warehouse.py first to create it.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def print_table(rows, headers):
    if not rows:
        print("no data found for this report.")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print("  ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))


def report_overview(conn):
    cur = conn.cursor()

    total_orders = cur.execute("SELECT COUNT(*) FROM unified_sales").fetchone()[0]
    total_revenue = cur.execute("SELECT ROUND(SUM(line_total_inr), 2) FROM unified_sales").fetchone()[0]
    date_range = cur.execute("SELECT MIN(order_date), MAX(order_date) FROM unified_sales").fetchone()
    num_companies = cur.execute("SELECT COUNT(DISTINCT source_company) FROM unified_sales").fetchone()[0]
    num_categories = cur.execute("SELECT COUNT(DISTINCT category) FROM unified_sales").fetchone()[0]

    print("=== fmcg data platform: business overview ===")
    print(f"total orders (both companies) : {total_orders}")
    print(f"total revenue (inr)           : {total_revenue}")
    print(f"date range                    : {date_range[0]} to {date_range[1]}")
    print(f"source companies merged       : {num_companies}")
    print(f"unified product categories    : {num_categories}")


def report_monthly_revenue(conn, month=None):
    cur = conn.cursor()
    if month:
        rows = cur.execute(
            "SELECT * FROM monthly_revenue WHERE month = ?", (month,)
        ).fetchall()
        if not rows:
            print(f"no revenue data found for month '{month}'.")
            print("expected format is YYYY-MM, for example 2023-06.")
            return
    else:
        rows = cur.execute("SELECT * FROM monthly_revenue ORDER BY month").fetchall()

    print_table(rows, ["month", "total_orders", "total_revenue_inr", "avg_order_value_inr"])


def report_category_performance(conn):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM category_performance ORDER BY total_revenue_inr DESC"
    ).fetchall()
    print_table(rows, ["category", "total_units_sold", "total_revenue_inr", "num_orders", "avg_order_value_inr"])


def report_region_performance(conn):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM region_performance ORDER BY total_revenue_inr DESC"
    ).fetchall()
    print_table(rows, ["region", "total_orders", "total_revenue_inr"])


def report_company_comparison(conn):
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM company_comparison").fetchall()
    print_table(rows, ["source_company", "total_orders", "total_units_sold", "total_revenue_inr", "avg_order_value_inr"])


def report_payment_modes(conn):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM payment_mode_summary ORDER BY total_revenue_inr DESC"
    ).fetchall()
    print_table(rows, ["payment_mode", "total_orders", "total_revenue_inr", "pct_of_total_revenue"])


def report_top_products(conn, limit=15, category=None):
    cur = conn.cursor()
    if category:
        rows = cur.execute(
            "SELECT * FROM top_products WHERE category = ? ORDER BY total_revenue_inr DESC LIMIT ?",
            (category, limit),
        ).fetchall()
        if not rows:
            valid = [r[0] for r in cur.execute("SELECT DISTINCT category FROM top_products").fetchall()]
            print(f"no products found in category '{category}'.")
            print(f"available categories: {', '.join(sorted(valid))}")
            return
    else:
        rows = cur.execute(
            "SELECT * FROM top_products ORDER BY total_revenue_inr DESC LIMIT ?", (limit,)
        ).fetchall()

    print_table(rows, ["product_name", "category", "source_company", "total_units_sold", "total_revenue_inr"])


def build_parser():
    parser = argparse.ArgumentParser(
        description="command line reporting tool for the fmcg data warehouse (gold layer)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("overview", help="overall business overview across both companies")

    mr = subparsers.add_parser("monthly-revenue", help="monthly revenue trend")
    mr.add_argument("--month", help="filter to a single month, format YYYY-MM")

    subparsers.add_parser("category-performance", help="revenue and units sold per category")
    subparsers.add_parser("region-performance", help="revenue per region")
    subparsers.add_parser("company-comparison", help="company a vs company b performance")
    subparsers.add_parser("payment-modes", help="revenue split by payment mode")

    tp = subparsers.add_parser("top-products", help="top selling products by revenue")
    tp.add_argument("--limit", type=int, default=15, help="number of products to show, default 15")
    tp.add_argument("--category", help="filter to a specific category")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    conn = get_connection()

    try:
        if args.command == "overview":
            report_overview(conn)
        elif args.command == "monthly-revenue":
            report_monthly_revenue(conn, month=args.month)
        elif args.command == "category-performance":
            report_category_performance(conn)
        elif args.command == "region-performance":
            report_region_performance(conn)
        elif args.command == "company-comparison":
            report_company_comparison(conn)
        elif args.command == "payment-modes":
            report_payment_modes(conn)
        elif args.command == "top-products":
            if args.limit <= 0:
                print("error: --limit must be a positive number.")
                sys.exit(1)
            report_top_products(conn, limit=args.limit, category=args.category)
    except sqlite3.Error as e:
        print(f"database error: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
