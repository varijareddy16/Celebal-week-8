# fmcg data consolidation and analytics platform

after an acquisition, two fmcg companies had sales data in completely
different formats. this project builds a small data pipeline that pulls
both sources together, cleans and standardizes them, and produces
business-ready tables for reporting, following the medallion
architecture (bronze, silver, gold).

no real power bi or databricks account was available for this project,
so a sqlite warehouse plus a command line reporting tool stands in for
that layer. the gold layer csv files are exactly what you would connect
to power bi or databricks sql in a real setup.

## architecture

```
company a (csv export)  ---\
                              >---  bronze  --->  silver  --->  gold  --->  reporting
company b (api / json)  ---/       (raw)         (cleaned,      (business   (sqlite +
                                                   unified)       ready)      cli, would
                                                                              be power bi
                                                                              in production)
```

- **bronze**: raw data exactly as it would arrive from each source, untouched
- **silver**: cleaned, validated, and merged into one consistent schema
- **gold**: aggregated tables built specifically to answer business questions
- **warehouse / reporting**: gold tables loaded into sqlite, queried by the cli tool

## project structure

```
fmcg_data_platform/
├── scripts/
│   ├── generate_bronze_data.py    simulates the two raw company sources
│   ├── silver_transform.py        cleans and unifies both sources
│   ├── gold_aggregate.py          builds business-ready aggregated tables
│   └── build_warehouse.py         loads gold tables into sqlite
├── report_cli.py                  command line reporting tool
├── bronze/                        raw data (company a csv, company b json)
├── silver/                        unified_sales.csv, the cleaned merged table
├── gold/                          business-ready aggregated csv tables
├── reports/                       cleaning/transform logs
└── fmcg_warehouse.db              sqlite warehouse (created by build_warehouse.py)
```

## how to run it

run these in order, from inside the `fmcg_data_platform` folder:

```bash
python3 scripts/generate_bronze_data.py
python3 scripts/silver_transform.py
python3 scripts/gold_aggregate.py
python3 scripts/build_warehouse.py
```

after that, the warehouse is ready and you can run any report:

```bash
python3 report_cli.py overview
python3 report_cli.py monthly-revenue
python3 report_cli.py monthly-revenue --month 2023-06
python3 report_cli.py category-performance
python3 report_cli.py region-performance
python3 report_cli.py company-comparison
python3 report_cli.py payment-modes
python3 report_cli.py top-products
python3 report_cli.py top-products --limit 5 --category Snacks
```

run `python3 report_cli.py --help` to see all reports and options.

## the data mismatch problem (and how it was solved)

company a and company b used completely different conventions, on purpose,
to mirror what actually happens after an acquisition:

| issue                  | company a                  | company b                        |
|------------------------|-----------------------------|-----------------------------------|
| source format          | csv export                  | json (simulated api pull)         |
| date format            | YYYY-MM-DD                  | DD-MM-YYYY                        |
| currency                | INR directly                 | USD, needed conversion to INR     |
| category naming        | "Edible Oils"                | "Cooking Oils"                    |
| region naming          | "North Zone"                 | "North"                           |
| column names           | order_id, order_date, ...    | transactionId, txnDate, ...       |

`silver_transform.py` renames every column to one shared schema, parses
both date formats, converts company b's usd prices to inr using a fixed
exchange rate, and maps both companies' category and region names onto
one shared set of values. the result is `silver/unified_sales.csv`, a
single table where a row from either company looks identical in
structure.

## gold layer tables

| table                       | answers                                            |
|------------------------------|----------------------------------------------------|
| monthly_revenue.csv          | how is revenue trending month over month           |
| category_performance.csv     | which product categories perform best              |
| region_performance.csv       | which regions generate the most revenue            |
| company_comparison.csv       | how does company a compare to company b post-merge |
| payment_mode_summary.csv     | how do customers prefer to pay                      |
| top_products.csv             | which individual products sell the most            |

## edge cases the cli tool handles

- warehouse file missing → clear message telling you to run build_warehouse.py first
- unknown category passed to `top-products` → lists the valid categories
- month with no data passed to `monthly-revenue` → clear message, no crash
- negative or zero `--limit` → rejected with an error message before querying
- unknown subcommand or missing arguments → argparse prints usage and exits

## note on power bi / databricks

this project was built and tested locally in python and sqlite since no
power bi or databricks workspace was available. the gold layer csv
files (or the equivalent sqlite tables) are structured so they could be
loaded directly into either tool without any further transformation, if
access becomes available later.
