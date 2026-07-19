"""
report_cli.py

command line reporting tool for the e-commerce analytics database.
run this after generate_data.py, data_cleaning.py, and database_setup.py
have been run, in that order.

usage examples:

    python report_cli.py summary
    python report_cli.py revenue-trend
    python report_cli.py revenue-trend --month 2023-06
    python report_cli.py segments
    python report_cli.py cohort
    python report_cli.py top-products --limit 5
    python report_cli.py top-products --category Electronics
    python report_cli.py customer 42
    python report_cli.py payment-methods
    python report_cli.py repeat-customers

run "python report_cli.py --help" to see all available reports.
"""

import argparse
import sqlite3
import os
import sys

DB_PATH = "ecommerce.db"


def get_connection():
    if not os.path.exists(DB_PATH):
        print(f"error: database file '{DB_PATH}' not found.")
        print("run database_setup.py first to create it.")
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


# ---------------------------------------------------------------------------
# report: overall summary
# ---------------------------------------------------------------------------
def report_summary(conn):
    cur = conn.cursor()

    total_customers = cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_orders = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

    total_revenue = cur.execute("""
        SELECT ROUND(SUM(oi.line_total), 2)
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.status != 'Cancelled'
    """).fetchone()[0] or 0

    date_range = cur.execute("""
        SELECT MIN(order_date), MAX(order_date) FROM orders WHERE order_date IS NOT NULL
    """).fetchone()

    print("=== business summary ===")
    print(f"total customers      : {total_customers}")
    print(f"total products       : {total_products}")
    print(f"total orders         : {total_orders}")
    print(f"total revenue        : {total_revenue}")
    print(f"order date range     : {date_range[0]} to {date_range[1]}")


# ---------------------------------------------------------------------------
# report: monthly revenue trend
# ---------------------------------------------------------------------------
def report_revenue_trend(conn, month=None):
    cur = conn.cursor()

    if month:
        query = """
            WITH monthly_revenue AS (
                SELECT strftime('%Y-%m', o.order_date) AS month,
                    COUNT(DISTINCT o.order_id) AS total_orders,
                    ROUND(SUM(oi.line_total), 2) AS total_revenue
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_date IS NOT NULL AND o.status != 'Cancelled'
                GROUP BY month
            )
            SELECT * FROM monthly_revenue WHERE month = ?
        """
        rows = cur.execute(query, (month,)).fetchall()
        if not rows:
            print(f"no revenue data found for month '{month}'.")
            print("expected format is YYYY-MM, for example 2023-06.")
            return
        print_table(rows, ["month", "total_orders", "total_revenue"])
        return

    query = """
        WITH monthly_revenue AS (
            SELECT strftime('%Y-%m', o.order_date) AS month,
                ROUND(SUM(oi.line_total), 2) AS revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.order_date IS NOT NULL AND o.status != 'Cancelled'
            GROUP BY month
        )
        SELECT
            month,
            revenue,
            LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
            ROUND(
                (revenue - LAG(revenue) OVER (ORDER BY month)) * 100.0
                / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 2
            ) AS pct_growth
        FROM monthly_revenue
        ORDER BY month
    """
    rows = cur.execute(query).fetchall()
    print_table(rows, ["month", "revenue", "prev_month_revenue", "pct_growth"])


# ---------------------------------------------------------------------------
# report: customer segmentation (rfm)
# ---------------------------------------------------------------------------
def report_segments(conn, limit=20):
    cur = conn.cursor()
    query = """
        WITH customer_orders AS (
            SELECT o.customer_id,
                COUNT(DISTINCT o.order_id) AS frequency,
                ROUND(SUM(oi.line_total), 2) AS monetary,
                MAX(o.order_date) AS last_order_date
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status != 'Cancelled'
            GROUP BY o.customer_id
        ),
        rfm_scores AS (
            SELECT customer_id, frequency, monetary, last_order_date,
                CAST(julianday('2024-07-01') - julianday(last_order_date) AS INTEGER) AS recency_days,
                NTILE(4) OVER (ORDER BY julianday(last_order_date) DESC) AS recency_score,
                NTILE(4) OVER (ORDER BY frequency ASC) AS frequency_score,
                NTILE(4) OVER (ORDER BY monetary ASC) AS monetary_score
            FROM customer_orders
        )
        SELECT customer_id, recency_days, frequency, monetary,
            (recency_score + frequency_score + monetary_score) AS rfm_total,
            CASE
                WHEN (recency_score + frequency_score + monetary_score) >= 10 THEN 'Champions'
                WHEN (recency_score + frequency_score + monetary_score) >= 8 THEN 'Loyal Customers'
                WHEN (recency_score + frequency_score + monetary_score) >= 6 THEN 'Potential Loyalists'
                WHEN (recency_score + frequency_score + monetary_score) >= 4 THEN 'At Risk'
                ELSE 'Lost'
            END AS segment
        FROM rfm_scores
        ORDER BY rfm_total DESC
        LIMIT ?
    """
    rows = cur.execute(query, (limit,)).fetchall()
    print_table(rows, ["customer_id", "recency_days", "frequency", "monetary", "rfm_total", "segment"])

    print("\nsegment counts (across all customers):")
    count_query = """
        WITH customer_orders AS (
            SELECT o.customer_id,
                COUNT(DISTINCT o.order_id) AS frequency,
                ROUND(SUM(oi.line_total), 2) AS monetary,
                MAX(o.order_date) AS last_order_date
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status != 'Cancelled'
            GROUP BY o.customer_id
        ),
        rfm_scores AS (
            SELECT customer_id,
                NTILE(4) OVER (ORDER BY julianday(last_order_date) DESC) AS recency_score,
                NTILE(4) OVER (ORDER BY frequency ASC) AS frequency_score,
                NTILE(4) OVER (ORDER BY monetary ASC) AS monetary_score
            FROM customer_orders
        ),
        segmented AS (
            SELECT customer_id,
                CASE
                    WHEN (recency_score + frequency_score + monetary_score) >= 10 THEN 'Champions'
                    WHEN (recency_score + frequency_score + monetary_score) >= 8 THEN 'Loyal Customers'
                    WHEN (recency_score + frequency_score + monetary_score) >= 6 THEN 'Potential Loyalists'
                    WHEN (recency_score + frequency_score + monetary_score) >= 4 THEN 'At Risk'
                    ELSE 'Lost'
                END AS segment
            FROM rfm_scores
        )
        SELECT segment, COUNT(*) AS num_customers
        FROM segmented
        GROUP BY segment
        ORDER BY num_customers DESC
    """
    seg_rows = cur.execute(count_query).fetchall()
    print_table(seg_rows, ["segment", "num_customers"])


# ---------------------------------------------------------------------------
# report: cohort retention analysis
# ---------------------------------------------------------------------------
def report_cohort(conn):
    cur = conn.cursor()
    query = """
        WITH cohorts AS (
            SELECT customer_id, strftime('%Y-%m', signup_date) AS cohort_month
            FROM customers
            WHERE signup_date IS NOT NULL
        ),
        customer_activity AS (
            SELECT o.customer_id, strftime('%Y-%m', o.order_date) AS activity_month
            FROM orders o
            WHERE o.order_date IS NOT NULL AND o.status != 'Cancelled'
        ),
        cohort_activity AS (
            SELECT
                c.cohort_month,
                ca.activity_month,
                (CAST(strftime('%Y', ca.activity_month || '-01') AS INTEGER) * 12
                    + CAST(strftime('%m', ca.activity_month || '-01') AS INTEGER))
                -
                (CAST(strftime('%Y', c.cohort_month || '-01') AS INTEGER) * 12
                    + CAST(strftime('%m', c.cohort_month || '-01') AS INTEGER)) AS month_number,
                c.customer_id
            FROM cohorts c
            JOIN customer_activity ca ON c.customer_id = ca.customer_id
            WHERE ca.activity_month >= c.cohort_month
        ),
        cohort_size AS (
            SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
            FROM cohorts
            GROUP BY cohort_month
        )
        SELECT
            ca.cohort_month,
            ca.month_number,
            COUNT(DISTINCT ca.customer_id) AS active_customers,
            cs.cohort_customers,
            ROUND(COUNT(DISTINCT ca.customer_id) * 100.0 / cs.cohort_customers, 1) AS retention_pct
        FROM cohort_activity ca
        JOIN cohort_size cs ON ca.cohort_month = cs.cohort_month
        WHERE ca.month_number BETWEEN 0 AND 6
        GROUP BY ca.cohort_month, ca.month_number
        ORDER BY ca.cohort_month, ca.month_number
    """
    rows = cur.execute(query).fetchall()
    print_table(rows, ["cohort_month", "months_since_signup", "active_customers", "cohort_size", "retention_pct"])


# ---------------------------------------------------------------------------
# report: top products (overall or by category), with rank in category
# ---------------------------------------------------------------------------
def report_top_products(conn, limit=10, category=None):
    cur = conn.cursor()

    base_query = """
        WITH product_revenue AS (
            SELECT p.product_id, p.product_name, p.category,
                SUM(oi.quantity) AS units_sold,
                ROUND(SUM(oi.line_total), 2) AS total_revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status != 'Cancelled'
            GROUP BY p.product_id, p.product_name, p.category
        ),
        ranked AS (
            SELECT *,
                RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
            FROM product_revenue
        )
        SELECT category, product_name, units_sold, total_revenue, rank_in_category
        FROM ranked
    """

    if category:
        query = base_query + " WHERE category = ? ORDER BY total_revenue DESC LIMIT ?"
        rows = cur.execute(query, (category, limit)).fetchall()
        if not rows:
            valid_categories = [r[0] for r in cur.execute("SELECT DISTINCT category FROM products").fetchall()]
            print(f"no products found in category '{category}'.")
            print(f"available categories: {', '.join(sorted(str(c) for c in valid_categories if c))}")
            return
    else:
        query = base_query + " ORDER BY total_revenue DESC LIMIT ?"
        rows = cur.execute(query, (limit,)).fetchall()

    print_table(rows, ["category", "product_name", "units_sold", "total_revenue", "rank_in_category"])


# ---------------------------------------------------------------------------
# report: single customer lookup
# ---------------------------------------------------------------------------
def report_customer(conn, customer_id):
    cur = conn.cursor()

    customer = cur.execute(
        "SELECT customer_id, name, email, city, signup_date FROM customers WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()

    if not customer:
        print(f"no customer found with customer_id = {customer_id}.")
        return

    print("=== customer details ===")
    print(f"customer_id  : {customer['customer_id']}")
    print(f"name         : {customer['name']}")
    print(f"email        : {customer['email']}")
    print(f"city         : {customer['city']}")
    print(f"signup_date  : {customer['signup_date']}")

    orders = cur.execute("""
        SELECT o.order_id, o.order_date, o.status,
            ROUND(SUM(oi.line_total), 2) AS order_total
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.customer_id = ?
        GROUP BY o.order_id, o.order_date, o.status
        ORDER BY o.order_date
    """, (customer_id,)).fetchall()

    print(f"\ntotal orders placed: {len(orders)}")
    if orders:
        print_table(orders, ["order_id", "order_date", "status", "order_total"])
    else:
        print("this customer has not placed any orders yet.")


# ---------------------------------------------------------------------------
# report: payment method breakdown and cancellation rate
# ---------------------------------------------------------------------------
def report_payment_methods(conn):
    cur = conn.cursor()
    query = """
        SELECT payment_method,
            COUNT(*) AS total_orders,
            SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
            SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) AS returned_orders,
            ROUND(SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS cancellation_rate_pct
        FROM orders
        GROUP BY payment_method
        ORDER BY total_orders DESC
    """
    rows = cur.execute(query).fetchall()
    print_table(rows, ["payment_method", "total_orders", "cancelled", "returned", "cancellation_rate_pct"])


# ---------------------------------------------------------------------------
# report: repeat vs one-time customers
# ---------------------------------------------------------------------------
def report_repeat_customers(conn):
    cur = conn.cursor()
    query = """
        WITH order_counts AS (
            SELECT customer_id, COUNT(DISTINCT order_id) AS num_orders
            FROM orders
            WHERE status != 'Cancelled'
            GROUP BY customer_id
        )
        SELECT
            CASE WHEN num_orders = 1 THEN 'One-time customer' ELSE 'Repeat customer' END AS customer_type,
            COUNT(*) AS num_customers,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_of_customers
        FROM order_counts
        GROUP BY customer_type
    """
    rows = cur.execute(query).fetchall()
    print_table(rows, ["customer_type", "num_customers", "pct_of_customers"])


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        description="command line reporting tool for the e-commerce analytics database"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="overall business summary")

    rt = subparsers.add_parser("revenue-trend", help="monthly revenue trend with growth")
    rt.add_argument("--month", help="filter to a single month, format YYYY-MM")

    seg = subparsers.add_parser("segments", help="rfm customer segmentation")
    seg.add_argument("--limit", type=int, default=20, help="number of customers to show, default 20")

    subparsers.add_parser("cohort", help="monthly cohort retention analysis")

    tp = subparsers.add_parser("top-products", help="top products by revenue")
    tp.add_argument("--limit", type=int, default=10, help="number of products to show, default 10")
    tp.add_argument("--category", help="filter to a specific category")

    cust = subparsers.add_parser("customer", help="look up a single customer by id")
    cust.add_argument("customer_id", type=int, help="the customer_id to look up")

    subparsers.add_parser("payment-methods", help="order breakdown and cancellation rate by payment method")

    subparsers.add_parser("repeat-customers", help="repeat vs one-time customer breakdown")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    conn = get_connection()

    try:
        if args.command == "summary":
            report_summary(conn)
        elif args.command == "revenue-trend":
            report_revenue_trend(conn, month=args.month)
        elif args.command == "segments":
            if args.limit <= 0:
                print("error: --limit must be a positive number.")
                sys.exit(1)
            report_segments(conn, limit=args.limit)
        elif args.command == "cohort":
            report_cohort(conn)
        elif args.command == "top-products":
            if args.limit <= 0:
                print("error: --limit must be a positive number.")
                sys.exit(1)
            report_top_products(conn, limit=args.limit, category=args.category)
        elif args.command == "customer":
            report_customer(conn, args.customer_id)
        elif args.command == "payment-methods":
            report_payment_methods(conn)
        elif args.command == "repeat-customers":
            report_repeat_customers(conn)
    except sqlite3.Error as e:
        print(f"database error: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
