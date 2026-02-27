from pathlib import Path
import polars as pl

p = Path(__file__).resolve()
project_root = p.parents[3]
in_data_dir = project_root / "flat_data" / "in" / "raw_data"
out_data_dir = project_root / "flat_data" / "out"

level_one = ["school", "student", "teacher"]
level_two = [
    # "accountability",
    "edunomics",
    # "demographics",
    # "effectiveness",
    # "experience",
]

for one in level_one:
    for two in level_two:
        sub_dir = in_data_dir / one / two
        if not sub_dir.exists():
            continue
        dfs = []
        for file in sub_dir.rglob("*.csv"):
            try:
                df = pl.read_csv(sub_dir / file, ignore_errors=True)
                print(len(df.columns))
                out_path = out_data_dir / f"{one}_{two}.csv"
                dfs.append(df)
                # lf.sink_csv(out_path)
            except Exception as e:
                print(f"Error {e} for {sub_dir}")
        out_path = out_data_dir / f"{one}_{two}.csv"
        df = pl.concat(dfs, how="diagonal_relaxed")
        df.write_csv(out_path)
