"""
gold_aggregate.py

reads the unified silver table and builds the gold layer: aggregated,
business-ready tables meant to be plugged straight into a bi tool like
power bi or databricks sql. each table here answers one specific
business question, which is the point of the gold layer.

tables produced:
- monthly_revenue.csv        total revenue and orders per month
- category_performance.csv   revenue and units sold per category
- region_performance.csv     revenue per region
- company_comparison.csv     side by side company a vs company b performance
- payment_mode_summary.csv   revenue split by payment mode
- top_products.csv           top selling products by revenue
"""

import pandas as pd
import os

SILVER_DIR = "silver"
GOLD_DIR = "gold"

os.makedirs(GOLD_DIR, exist_ok=True)


def load_unified():
    df = pd.read_csv(f"{SILVER_DIR}/unified_sales.csv", parse_dates=["order_date"])
    return df


def build_monthly_revenue(df):
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    monthly = df.groupby("month").agg(
        total_orders=("order_id", "count"),
        total_revenue_inr=("line_total_inr", "sum"),
    ).reset_index()
    monthly["total_revenue_inr"] = monthly["total_revenue_inr"].round(2)
    monthly["avg_order_value_inr"] = (
        monthly["total_revenue_inr"] / monthly["total_orders"]
    ).round(2)
    monthly = monthly.sort_values("month")
    monthly.to_csv(f"{GOLD_DIR}/monthly_revenue.csv", index=False)
    print(f"wrote {len(monthly)} rows to gold/monthly_revenue.csv")
    return monthly


def build_category_performance(df):
    cat = df.groupby("category").agg(
        total_units_sold=("quantity", "sum"),
        total_revenue_inr=("line_total_inr", "sum"),
        num_orders=("order_id", "count"),
    ).reset_index()
    cat["total_revenue_inr"] = cat["total_revenue_inr"].round(2)
    cat["avg_order_value_inr"] = (cat["total_revenue_inr"] / cat["num_orders"]).round(2)
    cat = cat.sort_values("total_revenue_inr", ascending=False)
    cat.to_csv(f"{GOLD_DIR}/category_performance.csv", index=False)
    print(f"wrote {len(cat)} rows to gold/category_performance.csv")
    return cat


def build_region_performance(df):
    region = df.groupby("region").agg(
        total_orders=("order_id", "count"),
        total_revenue_inr=("line_total_inr", "sum"),
    ).reset_index()
    region["total_revenue_inr"] = region["total_revenue_inr"].round(2)
    region = region.sort_values("total_revenue_inr", ascending=False)
    region.to_csv(f"{GOLD_DIR}/region_performance.csv", index=False)
    print(f"wrote {len(region)} rows to gold/region_performance.csv")
    return region


def build_company_comparison(df):
    comp = df.groupby("source_company").agg(
        total_orders=("order_id", "count"),
        total_units_sold=("quantity", "sum"),
        total_revenue_inr=("line_total_inr", "sum"),
    ).reset_index()
    comp["total_revenue_inr"] = comp["total_revenue_inr"].round(2)
    comp["avg_order_value_inr"] = (comp["total_revenue_inr"] / comp["total_orders"]).round(2)
    comp.to_csv(f"{GOLD_DIR}/company_comparison.csv", index=False)
    print(f"wrote {len(comp)} rows to gold/company_comparison.csv")
    return comp


def build_payment_mode_summary(df):
    pay = df.groupby("payment_mode").agg(
        total_orders=("order_id", "count"),
        total_revenue_inr=("line_total_inr", "sum"),
    ).reset_index()
    pay["total_revenue_inr"] = pay["total_revenue_inr"].round(2)
    pay["pct_of_total_revenue"] = (
        pay["total_revenue_inr"] / pay["total_revenue_inr"].sum() * 100
    ).round(1)
    pay = pay.sort_values("total_revenue_inr", ascending=False)
    pay.to_csv(f"{GOLD_DIR}/payment_mode_summary.csv", index=False)
    print(f"wrote {len(pay)} rows to gold/payment_mode_summary.csv")
    return pay


def build_top_products(df, top_n=15):
    prod = df.groupby(["product_name", "category", "source_company"]).agg(
        total_units_sold=("quantity", "sum"),
        total_revenue_inr=("line_total_inr", "sum"),
    ).reset_index()
    prod["total_revenue_inr"] = prod["total_revenue_inr"].round(2)
    prod = prod.sort_values("total_revenue_inr", ascending=False).head(top_n)
    prod.to_csv(f"{GOLD_DIR}/top_products.csv", index=False)
    print(f"wrote {len(prod)} rows to gold/top_products.csv")
    return prod


if __name__ == "__main__":
    df = load_unified()
    print(f"loaded {len(df)} rows from silver layer\n")

    build_monthly_revenue(df)
    build_category_performance(df)
    build_region_performance(df)
    build_company_comparison(df)
    build_payment_mode_summary(df)
    build_top_products(df)

    print("\ngold layer build complete")
    print("these csv files are the tables that would be connected to power bi or databricks sql")
