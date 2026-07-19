# e-commerce data analytics system

an end-to-end data analytics project that generates messy e-commerce data,
cleans it with pandas, loads it into sqlite, and analyzes it with sql
(joins, window functions, ctes, cohort analysis), all wired up behind a
command line reporting tool.

## project structure

```
ecommerce_analytics/
├── generate_data.py          generates raw csv data with intentional issues
├── data_cleaning.py          pandas cleaning and validation
├── database_setup.py         builds sqlite schema and loads cleaned data
├── report_cli.py             command line reporting tool
├── sql/
│   └── analysis_queries.sql  all analytical sql queries, documented
├── data/
│   ├── raw/                  raw generated csv files (messy, before cleaning)
│   └── cleaned/              cleaned csv files (after data_cleaning.py)
├── reports/
│   └── cleaning_report.txt   log of what the cleaning step fixed
└── ecommerce.db              sqlite database (created by database_setup.py)
```

## how to run it

run these in order, from inside the `ecommerce_analytics` folder:

```bash
python3 generate_data.py
python3 data_cleaning.py
python3 database_setup.py
```

after that, the database is ready and you can run any report:

```bash
python3 report_cli.py summary
python3 report_cli.py revenue-trend
python3 report_cli.py revenue-trend --month 2023-06
python3 report_cli.py segments --limit 10
python3 report_cli.py cohort
python3 report_cli.py top-products --limit 5
python3 report_cli.py top-products --category Electronics
python3 report_cli.py customer 42
python3 report_cli.py payment-methods
python3 report_cli.py repeat-customers
```

run `python3 report_cli.py --help` to see all reports and their options.

## the four tables

| table         | key columns                                              |
|---------------|-----------------------------------------------------------|
| customers     | customer_id, name, email, city, phone, signup_date        |
| products      | product_id, product_name, category, price, stock_quantity |
| orders        | order_id, customer_id, order_date, status, payment_method |
| order_items   | order_item_id, order_id, product_id, quantity, unit_price, line_total |

`orders.customer_id` references `customers.customer_id`.
`order_items.order_id` references `orders.order_id`.
`order_items.product_id` references `products.product_id`.

## data quality issues built into the raw data (on purpose)

these are injected by `generate_data.py` so that `data_cleaning.py` has
real problems to solve, the same way a real data export usually looks:

- missing values in optional and sometimes required fields
- duplicate customer and order rows
- three different date formats mixed in the same column
- inconsistent text casing (UPPER, lower, Title) and stray whitespace
- prices stored as plain numbers, `Rs.1234.56`, or `1234.56 INR`
- negative stock quantities, negative or zero order quantities and prices
- orders that reference a customer_id that does not exist
- order_items that reference an order_id or product_id that does not exist
- a couple of completely blank rows

`data_cleaning.py` fixes all of these and prints a short report of exactly
what was changed and how many rows were affected. `database_setup.py` then
enforces primary keys, foreign keys, and check constraints (positive
prices/quantities, non-negative stock) directly in the sqlite schema, and
runs a `PRAGMA foreign_key_check` to confirm there are zero violations
after loading.

## sql techniques used (see sql/analysis_queries.sql)

- joins across all four tables
- aggregations (SUM, COUNT, AVG) with GROUP BY
- window functions: LAG, RANK, NTILE, running SUM() OVER
- CTEs (WITH clauses), including multiple chained CTEs
- cohort analysis: customers grouped by signup month, tracking what
  percentage of each cohort placed an order in each following month
- rfm-based customer segmentation (recency, frequency, monetary)

## edge cases the cli tool handles

- database file missing → clear message telling you to run database_setup.py
- unknown category passed to `top-products` → lists the valid categories
- unknown customer_id passed to `customer` → clear "not found" message
- month with no data passed to `revenue-trend` → clear message, no crash
- negative or zero `--limit` → rejected with an error message before querying
- unknown subcommand or missing arguments → argparse prints usage and exits
