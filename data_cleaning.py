"""
data_cleaning.py

reads the raw csv files and cleans them using pandas.
writes cleaned csv files to data/cleaned/ and prints a short cleaning
report so we can see exactly what was fixed and how many rows were affected.

cleaning steps covered here:
- drop fully blank rows
- fix column data types (ids, dates, numbers)
- parse dates that come in more than one format
- strip whitespace and normalize text casing
- remove duplicate rows
- clean price fields that have currency symbols or text mixed in
- drop or flag negative / zero quantities and prices
- check foreign key integrity between tables (orphan records)
- fill or flag missing values where it makes sense
"""

import pandas as pd
import numpy as np
import re
import os

RAW_DIR = "data/raw"
CLEAN_DIR = "data/cleaned"

os.makedirs(CLEAN_DIR, exist_ok=True)

report_lines = []


def log(message):
    print(message)
    report_lines.append(message)


def parse_mixed_date(value):
    # tries a few known formats since the raw data mixes them
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    value = str(value).strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]
    for fmt in formats:
        try:
            return pd.to_datetime(value, format=fmt)
        except ValueError:
            continue
    # last resort, let pandas guess
    return pd.to_datetime(value, errors="coerce")


def clean_price(value):
    # strips currency symbols and text like "Rs." or "INR" and converts to float
    if pd.isna(value) or str(value).strip() == "":
        return np.nan
    value = str(value).strip()
    # remove known currency words/symbols first so we do not leave behind
    # a stray dot from something like "Rs." (which would otherwise create
    # a second decimal point once digits are stripped)
    value = re.sub(r"(?i)rs\.?|inr", "", value)
    value = value.strip()
    # now keep only digits, a single leading minus, and dots
    value = re.sub(r"[^0-9.\-]", "", value)
    if value in ("", "-", "."):
        return np.nan
    try:
        return float(value)
    except ValueError:
        return np.nan


# ---------------------------------------------------------------------------
# customers
# ---------------------------------------------------------------------------
def clean_customers():
    log("\n=== cleaning customers ===")
    df = pd.read_csv(f"{RAW_DIR}/customers.csv", dtype=str)
    start_count = len(df)

    # drop rows where customer_id is missing, these are unusable
    df = df[df["customer_id"].notna() & (df["customer_id"].str.strip() != "")]
    log(f"dropped {start_count - len(df)} rows with missing customer_id")

    df["customer_id"] = df["customer_id"].astype(int)

    # strip whitespace on text columns
    for col in ["name", "email", "city", "phone"]:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace("nan", np.nan)

    # normalize casing
    df["name"] = df["name"].str.title()
    df["email"] = df["email"].str.lower()
    df["city"] = df["city"].str.title()

    # normalize phone numbers, keep only digits, take last 10
    def clean_phone(p):
        if pd.isna(p):
            return np.nan
        digits = re.sub(r"\D", "", str(p))
        return digits[-10:] if len(digits) >= 10 else np.nan

    df["phone"] = df["phone"].apply(clean_phone)

    # parse signup date
    df["signup_date"] = df["signup_date"].apply(parse_mixed_date)
    missing_dates = df["signup_date"].isna().sum()
    log(f"{missing_dates} rows have missing or unparseable signup_date")

    # drop exact duplicate rows (same customer_id and same data)
    before = len(df)
    df = df.drop_duplicates(subset=["customer_id"], keep="first")
    log(f"dropped {before - len(df)} duplicate customer_id rows")

    missing_email = df["email"].isna().sum()
    missing_city = df["city"].isna().sum()
    log(f"{missing_email} rows missing email, {missing_city} rows missing city (kept, flagged)")

    df = df.sort_values("customer_id").reset_index(drop=True)
    log(f"final customers row count: {len(df)}")
    return df


# ---------------------------------------------------------------------------
# products
# ---------------------------------------------------------------------------
def clean_products():
    log("\n=== cleaning products ===")
    df = pd.read_csv(f"{RAW_DIR}/products.csv", dtype=str)
    start_count = len(df)

    df = df[df["product_id"].notna()]
    df["product_id"] = df["product_id"].astype(int)

    df["category"] = df["category"].astype(str).str.strip().str.title()
    df["category"] = df["category"].replace("Nan", np.nan)

    df["price"] = df["price"].apply(clean_price)
    missing_price = df["price"].isna().sum()
    log(f"{missing_price} rows have missing or unparseable price")

    df["stock_quantity"] = pd.to_numeric(df["stock_quantity"], errors="coerce")

    negative_stock = (df["stock_quantity"] < 0).sum()
    log(f"{negative_stock} rows have negative stock_quantity, clipping to 0")
    df["stock_quantity"] = df["stock_quantity"].clip(lower=0)

    before = len(df)
    df = df.drop_duplicates(subset=["product_id"], keep="first")
    log(f"dropped {before - len(df)} duplicate product_id rows")

    df = df.sort_values("product_id").reset_index(drop=True)
    log(f"final products row count: {len(df)}")
    return df


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------
def clean_orders(valid_customer_ids):
    log("\n=== cleaning orders ===")
    df = pd.read_csv(f"{RAW_DIR}/orders.csv", dtype=str)
    start_count = len(df)

    df = df[df["order_id"].notna()]
    df["order_id"] = df["order_id"].astype(int)
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")

    df["order_date"] = df["order_date"].apply(parse_mixed_date)
    missing_dates = df["order_date"].isna().sum()
    log(f"{missing_dates} rows have missing or unparseable order_date")

    df["status"] = df["status"].astype(str).str.strip().str.title()
    df["status"] = df["status"].replace("Nan", "Unknown")

    before = len(df)
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    log(f"dropped {before - len(df)} duplicate order_id rows")

    # check foreign key integrity against customers table
    orphan_mask = ~df["customer_id"].isin(valid_customer_ids)
    orphan_count = orphan_mask.sum()
    log(f"{orphan_count} orders reference a customer_id that does not exist, dropping them")
    df = df[~orphan_mask]

    df = df.sort_values("order_id").reset_index(drop=True)
    log(f"final orders row count: {len(df)}")
    return df


# ---------------------------------------------------------------------------
# order_items
# ---------------------------------------------------------------------------
def clean_order_items(valid_order_ids, valid_product_ids):
    log("\n=== cleaning order_items ===")
    df = pd.read_csv(f"{RAW_DIR}/order_items.csv", dtype=str)

    df = df[df["order_item_id"].notna()]
    df["order_item_id"] = df["order_item_id"].astype(int)
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    # foreign key checks
    orphan_orders = ~df["order_id"].isin(valid_order_ids)
    log(f"{orphan_orders.sum()} order_items reference an order_id that does not exist, dropping them")
    df = df[~orphan_orders]

    orphan_products = ~df["product_id"].isin(valid_product_ids)
    log(f"{orphan_products.sum()} order_items reference a product_id that does not exist, dropping them")
    df = df[~orphan_products]

    bad_qty = (df["quantity"] <= 0) | df["quantity"].isna()
    log(f"{bad_qty.sum()} order_items have a zero, negative, or missing quantity, dropping them")
    df = df[~bad_qty]

    bad_price = (df["unit_price"] <= 0) | df["unit_price"].isna()
    log(f"{bad_price.sum()} order_items have a zero, negative, or missing unit_price, dropping them")
    df = df[~bad_price]

    df["quantity"] = df["quantity"].astype(int)
    df["order_id"] = df["order_id"].astype(int)
    df["product_id"] = df["product_id"].astype(int)

    df["line_total"] = round(df["quantity"] * df["unit_price"], 2)

    df = df.sort_values("order_item_id").reset_index(drop=True)
    log(f"final order_items row count: {len(df)}")
    return df


if __name__ == "__main__":
    customers = clean_customers()
    products = clean_products()
    orders = clean_orders(valid_customer_ids=set(customers["customer_id"]))
    order_items = clean_order_items(
        valid_order_ids=set(orders["order_id"]),
        valid_product_ids=set(products["product_id"]),
    )

    customers.to_csv(f"{CLEAN_DIR}/customers.csv", index=False)
    products.to_csv(f"{CLEAN_DIR}/products.csv", index=False)
    orders.to_csv(f"{CLEAN_DIR}/orders.csv", index=False)
    order_items.to_csv(f"{CLEAN_DIR}/order_items.csv", index=False)

    log("\ncleaned files written to data/cleaned/")

    with open("reports/cleaning_report.txt", "w") as f:
        f.write("\n".join(report_lines))
    print("\ncleaning report saved to reports/cleaning_report.txt")
