from pathlib import Path
import polars as pl
import json

p = Path(__file__).resolve()

project_root = p.parents[3]
raw_data_dir = project_root / "flat_data" / "in" / "raw_data"
out_data_dir = project_root / "flat_data" / "out"

metadata = []

for csv_path in out_data_dir.glob("*.csv"):
    # Treat the base filename (without extension) as the "sheet name"
    sheet_name = csv_path.stem

    # Read the CSV into a DataFrame
    df = pl.read_csv(str(csv_path), null_values="NA")

    # Get schema: ordered mapping of column name -> dtype
    schema = df.schema  # same as df.collect_schema() for DataFrame

    # Build column metadata
    columns = []
    for col_name, dtype in schema.items():
        columns.append(
            {
                "name": col_name,
                "dtype": str(dtype),  # convert Polars dtype to string
            }
        )

    metadata.append(
        {
            "file": csv_path.name,
            "sheet_name": sheet_name,
            "columns": columns,
        }
    )

# Write metadata to JSON in out_data_dir
json_path = out_data_dir / "schema_metadata.json"
with json_path.open("w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)
