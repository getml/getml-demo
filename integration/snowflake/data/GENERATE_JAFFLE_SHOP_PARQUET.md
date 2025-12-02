# Generate Parquet files from Jaffle Shop CSV data

This script reads the Jaffle Shop CSV files and converts them to Parquet format for more efficient storage and querying in Snowflake.

## Generate Jaffle Shop Data (CSV)

To generate the Jaffle Shop CSV data, run the following command:

```bash
pipx run jafgen 6
```

This will create the necessary CSV files in the `jaffle-data` directory.

## Convert CSV to Parquet

To convert the generated CSV files to Parquet format, run the following script:

```bash
python convert_jaffle_csv_to_parquet.py
```

This will read each CSV file from the `jaffle-data` directory and save the corresponding Parquet files in the `jaffle-data/parquet` directory.

## Upload Parquet Files to GCP

To upload the Parquet files to your GCP bucket, use the following commands:

```bash
gcloud config set project getml-infra
gcloud storage cp jaffle-data/parquet/*.parquet gs://static.getml.com/datasets/jaffle_shop/
```
