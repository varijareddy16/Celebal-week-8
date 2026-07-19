"""
silver_transform.py

reads both bronze sources (company a csv, company b json) and turns them
into one clean, unified table with a single consistent schema. this is
the silver layer: validated, standardized data, but not yet aggregated
for reporting.

steps done here:
- rename all columns to one common schema
- parse both date formats into a single standard format
- convert company b prices from usd to inr so both companies are
  comparable (using a fixed conversion rate for this project)
- standardize category names, since both companies name categories
  differently for the same kind of product
- standardize region names
- handle missing values
- add a source_company column so we always know where a row came from
- combine both into one unified_sales table
"""

import pandas as pd
import json
import os

BRONZE_DIR = "bronze"
SILVER_DIR = "silver"

os.makedirs(SILVER_DIR, exist_ok=True)

USD_TO_INR = 83.0

# maps company b's category names to the same categories company a uses
CATEGORY_MAP = {
    "Cooking Oils": "Edible Oils",
    "Household": "Home Care",
    "Beverages": "Beverages",
    "Personal Care": "Personal Care",
    "Snacks & Confectionery": "Snacks",
    "Staples & Grains": "Staples",
}

# maps company b's region names to company a's region naming style
REGION_MAP = {
    "North": "North Zone",
    "South": "South Zone",
    "East": "East Zone",
    "West": "West Zone",
}

report_lines = []


def log(message):
    print(message)
    report_lines.append(message)


def clean_company_a():
    log("=== cleaning company a (csv source) ===")
    df = pd.read_csv(f"{BRONZE_DIR}/company_a_sales.csv")
    start_count = len(df)

    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")
    missing_dates = df["order_date"].isna().sum()
    log(f"{missing_dates} rows have an unparseable order_date")

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    missing_qty = df["quantity"].isna().sum()
    log(f"{missing_qty} rows have a missing quantity, dropping them")
    df = df[df["quantity"].notna()]

    missing_region = df["region"].isna().sum() + (df["region"] == "").sum()
    df["region"] = df["region"].replace("", pd.NA)
    log(f"{missing_region} rows have a missing region, kept and flagged as Unknown")
    df["region"] = df["region"].fillna("Unknown")

    unified = pd.DataFrame({
        "order_id": df["order_id"],
        "order_date": df["order_date"],
        "product_name": df["product_name"].str.strip(),
        "category": df["category"].str.strip(),
        "quantity": df["quantity"].astype(int),
        "unit_price_inr": df["unit_price_inr"].round(2),
        "region": df["region"],
        "payment_mode": df["payment_mode"],
        "source_company": "Company A",
    })

    log(f"company a: {start_count} raw rows -> {len(unified)} cleaned rows")
    return unified


def clean_company_b():
    log("\n=== cleaning company b (json / api source) ===")
    with open(f"{BRONZE_DIR}/company_b_sales.json", "r", encoding="utf-8") as f:
        records = json.load(f)

    df = pd.DataFrame(records)
    start_count = len(df)

    df["txnDate"] = pd.to_datetime(df["txnDate"], format="%d-%m-%Y", errors="coerce")
    missing_dates = df["txnDate"].isna().sum()
    log(f"{missing_dates} rows have an unparseable txnDate")

    df["qtySold"] = pd.to_numeric(df["qtySold"], errors="coerce")
    missing_qty = df["qtySold"].isna().sum()
    log(f"{missing_qty} rows have a missing qtySold, dropping them")
    df = df[df["qtySold"].notna()]

    missing_region = df["salesRegion"].isna().sum()
    df["salesRegion"] = df["salesRegion"].fillna("Unknown")
    log(f"{missing_region} rows have a missing salesRegion, kept and flagged as Unknown")

    # convert usd prices to inr so both companies are on the same currency
    df["unit_price_inr"] = (df["unitPriceUsd"] * USD_TO_INR).round(2)

    # map company b's category and region naming onto company a's naming
    df["category_mapped"] = df["department"].map(CATEGORY_MAP)
    unmapped_categories = df["category_mapped"].isna().sum()
    log(f"{unmapped_categories} rows have a department with no category mapping, flagged as Unmapped")
    df["category_mapped"] = df["category_mapped"].fillna("Unmapped")

    df["region_mapped"] = df["salesRegion"].map(REGION_MAP)
    df["region_mapped"] = df["region_mapped"].fillna("Unknown")

    unified = pd.DataFrame({
        "order_id": df["transactionId"],
        "order_date": df["txnDate"],
        "product_name": df["itemName"].str.strip(),
        "category": df["category_mapped"],
        "quantity": df["qtySold"].astype(int),
        "unit_price_inr": df["unit_price_inr"],
        "region": df["region_mapped"],
        "payment_mode": df["paymentType"],
        "source_company": "Company B",
    })

    log(f"company b: {start_count} raw rows -> {len(unified)} cleaned rows")
    return unified


if __name__ == "__main__":
    company_a = clean_company_a()
    company_b = clean_company_b()

    log("\n=== merging both sources into one unified table ===")
    unified_sales = pd.concat([company_a, company_b], ignore_index=True)

    # drop exact duplicate order_ids across the merged set, just in case
    before = len(unified_sales)
    unified_sales = unified_sales.drop_duplicates(subset=["order_id"], keep="first")
    log(f"dropped {before - len(unified_sales)} duplicate order_id rows after merging")

    unified_sales["line_total_inr"] = (
        unified_sales["quantity"] * unified_sales["unit_price_inr"]
    ).round(2)

    unified_sales = unified_sales.sort_values("order_date").reset_index(drop=True)

    unified_sales.to_csv(f"{SILVER_DIR}/unified_sales.csv", index=False)
    log(f"\nfinal unified_sales row count: {len(unified_sales)}")
    log(f"silver layer written to {SILVER_DIR}/unified_sales.csv")

    with open("reports/silver_transform_report.txt", "w") as f:
        f.write("\n".join(report_lines))
    print("\ntransform report saved to reports/silver_transform_report.txt")
