"""
generate_bronze_data.py

simulates the raw data that would come in from two different companies
after an acquisition. this is the bronze layer: data lands here exactly
as it arrives from the source, with no cleaning applied.

company a  = the original company, exports data as csv
company b  = the newly acquired company, data comes from an api as json

the two sources intentionally use different column names, different date
formats, different product naming, and different currencies, since this
is exactly the kind of mismatch that happens after a company acquisition.
"""

import csv
import json
import random
from datetime import datetime, timedelta

random.seed(7)

NUM_A_RECORDS = 1500
NUM_B_RECORDS = 1200

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 6, 30)

# company a product catalog (fmcg style categories)
company_a_products = [
    ("Sunrich Cooking Oil 1L", "Edible Oils"),
    ("Sunrich Cooking Oil 5L", "Edible Oils"),
    ("FreshWash Detergent Powder 1kg", "Home Care"),
    ("FreshWash Dish Soap 500ml", "Home Care"),
    ("GoldTea Premium 250g", "Beverages"),
    ("GoldTea Green Tea 100g", "Beverages"),
    ("SoftCare Shampoo 200ml", "Personal Care"),
    ("SoftCare Body Wash 250ml", "Personal Care"),
    ("CrunchTime Biscuits 200g", "Snacks"),
    ("CrunchTime Chips 150g", "Snacks"),
    ("PureBite Atta 5kg", "Staples"),
    ("PureBite Rice 5kg", "Staples"),
]

# company b product catalog, uses different naming style entirely
company_b_products = [
    ("VITA Sunflower Oil 1 Litre", "Cooking Oils"),
    ("VITA Sunflower Oil 5 Litre", "Cooking Oils"),
    ("CleanPro Laundry Powder 1 KG", "Household"),
    ("CleanPro Dishwash Liquid 500 ML", "Household"),
    ("Chai Bliss Tea 250 GM", "Beverages"),
    ("Chai Bliss Green Tea 100 GM", "Beverages"),
    ("GlowUp Shampoo 200 ML", "Personal Care"),
    ("GlowUp Body Wash 250 ML", "Personal Care"),
    ("MunchBox Biscuits 200 GM", "Snacks & Confectionery"),
    ("MunchBox Chips 150 GM", "Snacks & Confectionery"),
    ("WholeGrain Atta 5 KG", "Staples & Grains"),
    ("WholeGrain Rice 5 KG", "Staples & Grains"),
]

regions = ["North", "South", "East", "West"]
company_a_regions = ["North Zone", "South Zone", "East Zone", "West Zone"]

payment_modes = ["Cash", "Card", "UPI", "Credit"]


def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


# ---------------------------------------------------------------------------
# company a: csv export, uses its own column naming and date format
# ---------------------------------------------------------------------------
def generate_company_a():
    rows = []
    for txn_id in range(1, NUM_A_RECORDS + 1):
        product_name, category = random.choice(company_a_products)
        qty = random.randint(1, 50)
        unit_price = round(random.uniform(40, 900), 2)
        txn_date = random_date(START_DATE, END_DATE)

        row = {
            "order_id": f"A-{txn_id:05d}",
            "order_date": txn_date.strftime("%Y-%m-%d"),
            "product_name": product_name,
            "category": category,
            "quantity": qty,
            "unit_price_inr": unit_price,
            "region": random.choice(company_a_regions),
            "payment_mode": random.choice(payment_modes),
        }

        # a few missing values, same as any real export
        if random.random() < 0.01:
            row["region"] = ""
        if random.random() < 0.01:
            row["quantity"] = ""

        rows.append(row)

    with open("bronze/company_a_sales.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to bronze/company_a_sales.csv")


# ---------------------------------------------------------------------------
# company b: simulated api pull, returns json, uses different field names,
# a different date format, and prices in a different currency field name
# ---------------------------------------------------------------------------
def generate_company_b():
    records = []
    for txn_id in range(1, NUM_B_RECORDS + 1):
        item_name, dept = random.choice(company_b_products)
        qty = random.randint(1, 50)
        price = round(random.uniform(0.5, 12), 2)  # stored in usd on their system
        txn_date = random_date(START_DATE, END_DATE)

        record = {
            "transactionId": f"B-{txn_id:05d}",
            "txnDate": txn_date.strftime("%d-%m-%Y"),
            "itemName": item_name,
            "department": dept,
            "qtySold": qty,
            "unitPriceUsd": price,
            "salesRegion": random.choice(regions),
            "paymentType": random.choice(payment_modes),
        }

        if random.random() < 0.015:
            record["salesRegion"] = None
        if random.random() < 0.01:
            record["qtySold"] = None

        records.append(record)

    with open("bronze/company_b_sales.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"wrote {len(records)} records to bronze/company_b_sales.json")


if __name__ == "__main__":
    generate_company_a()
    generate_company_b()
    print("bronze layer generation complete")
