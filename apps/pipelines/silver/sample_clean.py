import polars as pl
import os

def clean_data(input_path, output_path):
    """
    Sample cleaning script following Medallion architecture (Bronze -> Silver).
    """
    print(f"Reading raw data from {input_path}...")
    
    # Load raw data (Bronze layer)
    df = pl.read_csv(input_path)
    
    # Perform cleaning (Silver layer)
    # Example: Remove nulls, rename columns highlight trends
    df_cleaned = (
        df.lazy()
        .drop_nulls()
        .with_columns([
            pl.col("timestamp").str.to_datetime(),
            (pl.col("value") * 1.1).alias("adjusted_value")
        ])
        .collect()
    )
    
    print(f"Writing cleaned data to {output_path}...")
    df_cleaned.write_csv(output_path)

if __name__ == "__main__":
    # Example usage
    bronze_file = "apps/pipelines/bronze/raw_data.csv"
    silver_file = "apps/pipelines/silver/cleaned_data.csv"
    
    if os.path.exists(bronze_file):
        clean_data(bronze_file, silver_file)
    else:
        print(f"Please place a CSV file at {bronze_file} to run this sample.")
