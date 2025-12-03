from pathlib import Path

import pandas as pd

NAMES: list[str] = [
    "raw_customers",
    "raw_items",
    "raw_orders",
    "raw_products",
    "raw_stores",
    "raw_supplies",
    "raw_tweets",
]

JAFFLE_CSV_DATA_PATH = Path("jaffle-data")

if not JAFFLE_CSV_DATA_PATH.exists():
    raise FileNotFoundError(
        f"Jaffle CSV data path {JAFFLE_CSV_DATA_PATH} does not exist."
        " Please run `jafgen` to generate CSVs."
    )

JAFFLE_PARQUET_DATA_PATH = JAFFLE_CSV_DATA_PATH / "parquet"
Path.mkdir(JAFFLE_PARQUET_DATA_PATH, exist_ok=True)


for name in NAMES:
    csv_filepath = JAFFLE_CSV_DATA_PATH / f"{name}.csv"
    parquet_filepath = JAFFLE_PARQUET_DATA_PATH / f"{name}.parquet"
    print(f"Loading {csv_filepath}...")

    # 1. Read CSV into memory
    df: pd.DataFrame = pd.read_csv(csv_filepath)

    # 2. Write DataFrame to Parquet
    # 'index=False' prevents pandas from adding an extra index column
    df.to_parquet(parquet_filepath, index=False)

    print(f"Converted {name} to parquet format at {parquet_filepath}.")
