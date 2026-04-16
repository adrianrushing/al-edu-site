import polars as pl
from pathlib import Path
from datetime import datetime

# 1. Setup Configuration
# Using Pathlib is much cleaner for cross-platform paths
DATA_DIR = Path(__file__).resolve().parents[3] / "flat_data" / "out"
DB_URI = "postgresql://dev_user:dev_password@localhost:5433/eflt"


def clean_column_names(df: pl.DataFrame) -> pl.DataFrame:
    """Standardizes headers to snake_case for PostgreSQL."""
    clean_names = [
        col.lower()
        .strip()
        .replace(" / ", "_")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("%", "percent")
        for col in df.columns
    ]
    df.columns = clean_names
    return df


def ingest_files():
    # List all CSVs in the directory
    csv_files = list(DATA_DIR.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {DATA_DIR}")
        return

    for file_path in csv_files:
        table_name = (
            f"stg_{file_path.stem}"  # school_edunomics.csv -> stg_school_edunomics
        )
        print(f"🚀 Starting ingestion: {file_path.name} -> {table_name}")

        try:
            # 2. Read data (In Staging, we usually treat everything as string for safety)
            # infer_schema_length=0 forces all columns to be UTF8/String
            df = pl.read_csv(file_path, infer_schema_length=0)

            # 3. Add Metadata & Clean Headers
            df = df.pipe(clean_column_names).with_columns(
                [
                    pl.lit(file_path.name).alias("_source_file"),
                    pl.lit(datetime.now()).alias("_ingested_at"),
                ]
            )

            # 4. Write to Postgres
            # Using 'replace' for staging ensures a fresh start each run
            df.write_database(
                table_name=table_name,
                connection=DB_URI,
                if_table_exists="replace",
                engine="adbc",
            )

            print(f"✅ Successfully loaded {len(df)} rows into {table_name}")

        except Exception as e:
            print(f"❌ Failed to load {file_path.name}: {e}")


if __name__ == "__main__":
    start_time = datetime.now()
    ingest_files()
    print(f"\nTotal duration: {datetime.now() - start_time}")
