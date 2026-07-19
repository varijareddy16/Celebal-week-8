"""
build_warehouse.py

loads the gold layer csv files into a sqlite database. this database
plays the role that power bi or databricks sql would play in a real
setup, it is the query layer that reporting tools connect to.

run this after generate_bronze_data.py, silver_transform.py, and
gold_aggregate.py have all been run in that order.
"""

import sqlite3
import pandas as pd
import os

GOLD_DIR = "gold"
SILVER_DIR = "silver"
DB_PATH = "fmcg_warehouse.db"

TABLES = {
    "unified_sales": f"{SILVER_DIR}/unified_sales.csv",
    "monthly_revenue": f"{GOLD_DIR}/monthly_revenue.csv",
    "category_performance": f"{GOLD_DIR}/category_performance.csv",
    "region_performance": f"{GOLD_DIR}/region_performance.csv",
    "company_comparison": f"{GOLD_DIR}/company_comparison.csv",
    "payment_mode_summary": f"{GOLD_DIR}/payment_mode_summary.csv",
    "top_products": f"{GOLD_DIR}/top_products.csv",
}


def build_warehouse():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    for table_name, csv_path in TABLES.items():
        if not os.path.exists(csv_path):
            print(f"warning: {csv_path} not found, skipping {table_name}")
            continue
        df = pd.read_csv(csv_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"loaded {len(df)} rows into table '{table_name}'")

    conn.commit()
    conn.close()
    print(f"\nwarehouse ready at {DB_PATH}")
    print("in a real setup this is the layer power bi or databricks sql would connect to")


if __name__ == "__main__":
    build_warehouse()
