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
        " Please run `pipx run jafgen 6` to generate CSVs. (6 years)"
    )

JAFFLE_PARQUET_DATA_PATH: Path = JAFFLE_CSV_DATA_PATH / "parquet"
JAFFLE_PARQUET_DATA_PATH.mkdir(parents=True, exist_ok=True)


for name in NAMES:
    csv_filepath = JAFFLE_CSV_DATA_PATH / f"{name}.csv"
    parquet_filepath = JAFFLE_PARQUET_DATA_PATH / f"{name}.parquet"
    print(f"Loading {csv_filepath}...")

    df: pd.DataFrame = pd.read_csv(csv_filepath)

    # 'index=False' prevents adding an extra index column
    df.to_parquet(parquet_filepath, index=False)

    print(f"Converted {name} to parquet format at {parquet_filepath}.")
