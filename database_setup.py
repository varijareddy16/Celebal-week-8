"""
database_setup.py

creates the sqlite database and schema, then loads the cleaned csv files
into it. primary keys, foreign keys, and check constraints are defined
directly in the schema so the database itself enforces data integrity,
not just the pandas cleaning step.

run this after data_cleaning.py has produced the cleaned csv files.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "ecommerce.db"
CLEAN_DIR = "data/cleaned"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    city TEXT,
    phone TEXT,
    signup_date TEXT
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT,
    price REAL CHECK (price IS NULL OR price > 0),
    stock_quantity INTEGER CHECK (stock_quantity >= 0)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT,
    status TEXT,
    payment_method TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER CHECK (quantity > 0),
    unit_price REAL CHECK (unit_price > 0),
    line_total REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
"""


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    print("schema created")

    customers = pd.read_csv(f"{CLEAN_DIR}/customers.csv")
    products = pd.read_csv(f"{CLEAN_DIR}/products.csv")
    orders = pd.read_csv(f"{CLEAN_DIR}/orders.csv")
    order_items = pd.read_csv(f"{CLEAN_DIR}/order_items.csv")

    customers.to_sql("customers", conn, if_exists="append", index=False)
    products.to_sql("products", conn, if_exists="append", index=False)
    orders.to_sql("orders", conn, if_exists="append", index=False)
    order_items.to_sql("order_items", conn, if_exists="append", index=False)

    conn.commit()

    # sanity check row counts and foreign key integrity
    cur = conn.cursor()
    for table in ["customers", "products", "orders", "order_items"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows loaded")

    fk_check = cur.execute("PRAGMA foreign_key_check").fetchall()
    if fk_check:
        print(f"warning: {len(fk_check)} foreign key violations found")
    else:
        print("foreign key check passed, no violations")

    conn.close()
    print(f"database ready at {DB_PATH}")


if __name__ == "__main__":
    build_database()
