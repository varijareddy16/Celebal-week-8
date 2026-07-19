"""
generate_data.py

generates synthetic e-commerce data for the analytics project.
creates 4 raw csv files: customers, products, orders, order_items

the data has intentional problems mixed in on purpose, so that the
cleaning step (data_cleaning.py) has real issues to fix. this mirrors
how real e-commerce data exports usually look before anyone touches them.

problems introduced:
- missing values in optional and some required columns
- duplicate customer and order records
- inconsistent date formats (yyyy-mm-dd, dd/mm/yyyy, mm-dd-yyyy)
- inconsistent text casing (email, city, category)
- extra whitespace around strings
- negative or zero quantities and prices
- orders referencing customer_ids that do not exist (orphan foreign keys)
- order_items referencing product_ids that do not exist
- a few completely blank rows
- inconsistent phone number formats
- price stored as string with currency symbol in some rows
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

NUM_CUSTOMERS = 500
NUM_PRODUCTS = 120
NUM_ORDERS = 3000
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 6, 30)

first_names = ["aarav", "vivaan", "aditya", "vihaan", "arjun", "sai", "reyansh", "krishna",
               "ishaan", "rohan", "ananya", "diya", "priya", "sneha", "kavya", "riya",
               "isha", "aisha", "meera", "tara", "kabir", "aryan", "dev", "yash", "neha"]
last_names = ["sharma", "verma", "reddy", "gupta", "iyer", "nair", "kumar", "singh",
              "rao", "patel", "mehta", "shah", "das", "menon", "pillai", "chowdhury"]

cities = ["Hyderabad", "Bengaluru", "Mumbai", "Delhi", "Chennai", "Pune", "Kolkata",
          "Ahmedabad", "Jaipur", "Lucknow"]

categories = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Footwear",
              "Beauty", "Sports", "Toys", "Groceries", "Furniture"]

order_statuses = ["Delivered", "Shipped", "Cancelled", "Returned", "Processing"]
payment_methods = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Cash on Delivery"]


def random_date(start, end):
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def format_date_randomly(dt):
    # pick one of a few different date formats to simulate messy exports
    fmt_choice = random.random()
    if fmt_choice < 0.7:
        return dt.strftime("%Y-%m-%d")
    elif fmt_choice < 0.9:
        return dt.strftime("%d/%m/%Y")
    else:
        return dt.strftime("%m-%d-%Y")


def messy_case(text):
    # randomly mess up the casing to simulate inconsistent data entry
    choice = random.random()
    if choice < 0.3:
        return text.upper()
    elif choice < 0.6:
        return text.lower()
    elif choice < 0.75:
        return text.title()
    else:
        return text


def maybe_add_whitespace(text):
    if random.random() < 0.15:
        return f"  {text}  "
    return text


# ---------------------------------------------------------------------------
# customers
# ---------------------------------------------------------------------------
def generate_customers():
    customers = []
    used_emails = set()

    for cust_id in range(1, NUM_CUSTOMERS + 1):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"

        base_email = f"{fname}.{lname}{cust_id}@example.com"
        email = base_email
        if email in used_emails:
            email = f"{fname}.{lname}{cust_id}x@example.com"
        used_emails.add(email)

        city = random.choice(cities)
        signup_date = random_date(START_DATE, END_DATE - timedelta(days=1))

        phone_choice = random.random()
        if phone_choice < 0.4:
            phone = f"9{random.randint(100000000, 999999999)}"
        elif phone_choice < 0.7:
            phone = f"+91-9{random.randint(100000000, 999999999)}"
        else:
            phone = f"9{random.randint(100000000, 999999999)}"

        row = {
            "customer_id": cust_id,
            "name": maybe_add_whitespace(messy_case(name)),
            "email": messy_case(email) if random.random() < 0.2 else email,
            "city": maybe_add_whitespace(messy_case(city)),
            "phone": phone,
            "signup_date": format_date_randomly(signup_date),
        }

        # intentionally blank out some fields
        if random.random() < 0.03:
            row["email"] = ""
        if random.random() < 0.02:
            row["city"] = ""
        if random.random() < 0.02:
            row["phone"] = ""

        customers.append(row)

    # inject a handful of exact duplicate customer rows (same customer_id, re-appended)
    for _ in range(8):
        dup = random.choice(customers).copy()
        customers.append(dup)

    # inject one or two completely blank rows
    customers.append({"customer_id": "", "name": "", "email": "", "city": "", "phone": "", "signup_date": ""})

    random.shuffle(customers)
    return customers


# ---------------------------------------------------------------------------
# products
# ---------------------------------------------------------------------------
def generate_products():
    products = []
    for prod_id in range(1, NUM_PRODUCTS + 1):
        category = random.choice(categories)
        product_name = f"{category.split()[0]} Item {prod_id}"

        base_price = round(random.uniform(99, 25000), 2)
        price_choice = random.random()
        if price_choice < 0.85:
            price_str = str(base_price)
        elif price_choice < 0.95:
            price_str = f"Rs.{base_price}"
        else:
            price_str = f"{base_price:.2f} INR"

        row = {
            "product_id": prod_id,
            "product_name": product_name,
            "category": maybe_add_whitespace(messy_case(category)),
            "price": price_str,
            "stock_quantity": random.randint(-5, 500),  # negative values are a bug to catch
        }

        if random.random() < 0.02:
            row["category"] = ""
        if random.random() < 0.01:
            row["price"] = ""

        products.append(row)

    random.shuffle(products)
    return products


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------
def generate_orders():
    orders = []
    valid_customer_ids = list(range(1, NUM_CUSTOMERS + 1))

    for order_id in range(1, NUM_ORDERS + 1):
        # 2 percent of orders reference a customer_id that does not exist (orphan fk)
        if random.random() < 0.02:
            customer_id = NUM_CUSTOMERS + random.randint(1, 50)
        else:
            customer_id = random.choice(valid_customer_ids)

        order_date = random_date(START_DATE, END_DATE)
        status = random.choice(order_statuses)
        payment_method = random.choice(payment_methods)

        row = {
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": format_date_randomly(order_date),
            "status": messy_case(status) if random.random() < 0.3 else status,
            "payment_method": payment_method,
        }

        if random.random() < 0.015:
            row["order_date"] = ""
        if random.random() < 0.01:
            row["status"] = ""

        orders.append(row)

    # duplicate a few full order rows
    for _ in range(15):
        dup = random.choice(orders).copy()
        orders.append(dup)

    random.shuffle(orders)
    return orders


# ---------------------------------------------------------------------------
# order_items
# ---------------------------------------------------------------------------
def generate_order_items(orders):
    order_items = []
    item_id = 1
    valid_product_ids = list(range(1, NUM_PRODUCTS + 1))
    valid_order_ids = [o["order_id"] for o in orders]

    for order_id in valid_order_ids:
        num_items = random.randint(1, 4)
        for _ in range(num_items):
            # 1.5 percent of items reference a product_id that does not exist
            if random.random() < 0.015:
                product_id = NUM_PRODUCTS + random.randint(1, 20)
            else:
                product_id = random.choice(valid_product_ids)

            quantity = random.randint(1, 6)
            # a small fraction of rows get a bad quantity to catch during cleaning
            if random.random() < 0.02:
                quantity = random.choice([0, -1, -3])

            unit_price = round(random.uniform(99, 25000), 2)
            if random.random() < 0.01:
                unit_price = -abs(unit_price)  # negative price bug

            row = {
                "order_item_id": item_id,
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
            }
            order_items.append(row)
            item_id += 1

    return order_items


def write_csv(rows, filepath, fieldnames):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {filepath}")


if __name__ == "__main__":
    customers = generate_customers()
    products = generate_products()
    orders = generate_orders()
    order_items = generate_order_items(orders)

    write_csv(customers, "data/raw/customers.csv",
              ["customer_id", "name", "email", "city", "phone", "signup_date"])
    write_csv(products, "data/raw/products.csv",
              ["product_id", "product_name", "category", "price", "stock_quantity"])
    write_csv(orders, "data/raw/orders.csv",
              ["order_id", "customer_id", "order_date", "status", "payment_method"])
    write_csv(order_items, "data/raw/order_items.csv",
              ["order_item_id", "order_id", "product_id", "quantity", "unit_price"])

    print("data generation complete")
