from pathlib import Path
import polars as pl

p = Path(__file__).resolve()
project_root = p.parents[3]
raw_data_dir = project_root / "flat_data" / "in" / "raw_data"
out_data_dir = project_root / "flat_data" / "out"


def normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    df = df.rename(lambda name: name.lower())
    new_names = [name.strip() for name in df.columns]
    return df.rename(dict(zip(df.columns, new_names)))


def has_bad_header_cols(df: pl.DataFrame) -> bool:
    norm_cols = [c.strip().lower() for c in df.columns]
    return any("unnamed" in c or "duplicate" in c for c in norm_cols)


def process_dataframe(df: pl.DataFrame, out_path: Path) -> None:
    df = normalize_columns(df)
    df.write_csv(str(out_path))


for path in raw_data_dir.rglob("*"):
    if not path.is_file():
        continue

    suffix = path.suffix.lower()

    try:
        if suffix == ".xlsx":
            # First pass: read sheets with default header (row 1)
            sheets = pl.read_excel(source=str(path), sheet_id=0)

            if isinstance(sheets, dict):
                print(f"\n{path.name}\n{len(sheets)} pages")
                for sheet_name, df in sheets.items():
                    print(f"  Sheet: {sheet_name!r}")

                    if has_bad_header_cols(df):
                        print(
                            f"    Detected 'unnamed'/'duplicate' in header of {sheet_name!r}; "
                            "using row 3 as header"
                        )
                        # Re-read this sheet with xlsx2csv and skip_rows=2 so row 3 is header
                        df = pl.read_excel(
                            source=str(path),
                            sheet_name=sheet_name,
                            engine="xlsx2csv",
                            read_options={"skip_rows": 2},
                        )

                    csv_name = f"{path.stem}__{sheet_name}.csv"
                    csv_path = out_data_dir / csv_name
                    process_dataframe(df, csv_path)
            else:
                df = sheets
                print(f"\n{path.name}\n1 page")

                if has_bad_header_cols(df):
                    print(
                        "    Detected 'unnamed'/'duplicate' in header; using row 3 as header"
                    )
                    df = pl.read_excel(
                        source=str(path),
                        sheet_id=1,  # first sheet
                        engine="xlsx2csv",
                        read_options={"skip_rows": 2},
                    )

                for idx, col in enumerate(df.columns, start=1):
                    print(f"    Column {idx}: {col}")
                csv_path = out_data_dir / path.with_suffix(".csv").name
                process_dataframe(df, csv_path)

        elif suffix == ".csv":
            print(f"\n{path.name} (csv)")

            # Header-only read to inspect column names
            df_head = pl.read_csv(
                str(path),
                n_rows=0,
                infer_schema=False,
            )

            extra_read_args = {}
            if has_bad_header_cols(df_head):
                print(
                    "    Detected 'unnamed'/'duplicate' in header; using row 3 as header"
                )
                extra_read_args["skip_rows"] = 2  # header at row 3

            df = pl.read_csv(
                str(path),
                schema_overrides={"totenrl": pl.Float64, "GrwAsian": pl.Float64},
                **extra_read_args,
            )

            for idx, col in enumerate(df.columns, start=1):
                print(f"    Column {idx}: {col}")
            csv_path = out_data_dir / path.name
            process_dataframe(df, csv_path)

    except Exception as e:
        print(f"Error {e} for {path}")
