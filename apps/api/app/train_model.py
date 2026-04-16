import os
import pandas as pd
import numpy as np
import joblib
from sqlalchemy import create_engine
from scipy.stats import pearsonr
from statsmodels.stats.multitest import multipletests
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, r2_score

from config import settings


def main():
    print("Connecting to DB...")
    engine = create_engine(settings.database_url)

    # 1. Base Data
    base_query = """
    SELECT 
        o.school_key,
        o.year,
        o.ach_all,
        e.per_pupil_total_raw,
        e.nces_poverty,
        e.nces_freelunch,
        t.exp_rate,
        t.inexp_rate,
        i.nces_locale_type,
        CASE WHEN i.nces_charter THEN 1 ELSE 0 END as is_charter,
        CASE WHEN i.nces_magnet THEN 1 ELSE 0 END as is_magnet
    FROM core.fact_school_outcomes_wide o
    JOIN core.dim_school_info i ON o.school_key = i.school_key
    JOIN core.fact_edunomics e ON o.school_key = e.school_key AND o.year = e.year
    JOIN core.fact_teacher_experience t ON o.school_key = t.school_key AND o.year = t.year
    WHERE o.ach_all IS NOT NULL
      AND t.sub_population = 'All SubPopulation'
    """
    df_base = pd.read_sql(base_query, engine)

    # 2. Geo Data (pivoted in pandas)
    geo_query = """
    SELECT 
        c.school_key, 
        fgo.metric_code, 
        AVG(fgo.opportunity_score) as opp_score
    FROM core.bridge_school_geo_county c
    JOIN core.dim_geo_tract t ON t.county_fips = c.county_fips
    JOIN core.fact_geo_opportunity fgo ON fgo.geoid10 = t.geoid10
    WHERE fgo.metric_code IN ('COI', 'ED', 'HE')
    GROUP BY c.school_key, fgo.metric_code
    """
    df_geo = pd.read_sql(geo_query, engine)
    df_geo_pivot = df_geo.pivot_table(
        index=["school_key"], columns="metric_code", values="opp_score"
    ).reset_index()
    # rename columns
    df_geo_pivot.columns.name = None
    df_geo_pivot = df_geo_pivot.rename(
        columns={"COI": "geo_COI", "ED": "geo_ED", "HE": "geo_HE"}
    )

    # 3. Demographics (pivoted in pandas)
    demo_query = """
    SELECT school_key, year, race, demographic_count
    FROM core.fact_student_demographics
    WHERE ethnicity = 'All Ethnicity' AND race != 'All Race'
    """
    df_demo = pd.read_sql(demo_query, engine)
    df_demo_pivot = df_demo.pivot_table(
        index=["school_key", "year"],
        columns="race",
        values="demographic_count",
        aggfunc="sum",
    ).reset_index()
    df_demo_pivot.columns.name = None

    # Calculate percentages
    race_cols = [c for c in df_demo_pivot.columns if c not in ["school_key", "year"]]
    df_demo_pivot["total_students"] = df_demo_pivot[race_cols].sum(axis=1)
    for col in race_cols:
        # Create percentage column
        clean_name = "pct_" + col.lower().replace(" ", "_").replace("/", "_")
        df_demo_pivot[clean_name] = df_demo_pivot[col] / df_demo_pivot[
            "total_students"
        ].replace(0, np.nan)

    pct_cols = [c for c in df_demo_pivot.columns if c.startswith("pct_")]
    df_demo_final = df_demo_pivot[["school_key", "year"] + pct_cols]

    # Merge all datasets
    df = df_base.merge(df_geo_pivot, on=["school_key"], how="left")
    df = df.merge(df_demo_final, on=["school_key", "year"], how="left")

    # Drop rows without achievement
    df = df.dropna(subset=["ach_all"])

    print(f"Final Merged Data shape: {df.shape}")

    # Variables to predict
    targets = [
        "ach_all",
        "per_pupil_total_raw",
        "nces_poverty",
        "nces_freelunch",
        "exp_rate",
        "inexp_rate",
    ]

    # All possible numerical features
    numeric_features = [
        "per_pupil_total_raw",
        "nces_poverty",
        "nces_freelunch",
        "exp_rate",
        "inexp_rate",
        "is_charter",
        "is_magnet",
        "geo_COI",
        "geo_ED",
        "geo_HE",
    ] + pct_cols

    categorical_features = ["nces_locale_type"]

    for target in targets:
        print(f"\n{'=' * 50}\nTarget Variable: {target}\n{'=' * 50}")

        # We drop rows where the target is missing
        df_target = df.dropna(subset=[target]).copy()

        # Features available for this target (everything else)
        candidate_numeric = [f for f in numeric_features if f != target]

        # Drop numeric features that are 100% missing
        candidate_numeric = [
            f for f in candidate_numeric if df_target[f].notna().sum() > 0
        ]

        candidate_features = candidate_numeric + categorical_features

        # Impute missing values for correlation testing (using median)
        imputer = SimpleImputer(strategy="median")
        if candidate_numeric:
            df_target[candidate_numeric] = imputer.fit_transform(
                df_target[candidate_numeric]
            )

        print("\nRunning Hypothesis Testing (Chapter 13)...")
        p_values = []
        correlations = []
        tested_features = []

        # Only test numeric features for correlation
        for feature in candidate_numeric:
            corr, p_val = pearsonr(df_target[feature], df_target[target])
            correlations.append(corr)
            p_values.append(p_val)
            tested_features.append(feature)

        # Benjamini-Hochberg (FDR) Correction
        reject, pvals_corrected, _, _ = multipletests(
            p_values, alpha=0.05, method="fdr_bh"
        )

        selected_numeric = []
        for f, c, p, r in zip(tested_features, correlations, pvals_corrected, reject):
            is_significant = r
            if is_significant:
                selected_numeric.append(f)

        # Always include categorical locale for now, or just use it if we want.
        # To keep it simple, we'll just add locale.
        selected_features = selected_numeric + categorical_features

        if not selected_numeric:
            print("No features passed the significance threshold.")
            continue

        print(f"\nSelected Numeric Features for Modeling: {selected_numeric}")

        X = df_target[selected_features]
        y = df_target[target]

        # Build a preprocessor
        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, selected_numeric),
                ("cat", categorical_transformer, categorical_features),
            ]
        )

        print("\nTraining Models...")
        # Deep Learning is powerful, let's use it alongside Linear Regression
        models = {
            "Linear Regression": Pipeline(
                steps=[
                    ("preprocessor", preprocessor),
                    ("regressor", LinearRegression()),
                ]
            ),
            "Deep Learning (MLP)": Pipeline(
                steps=[
                    ("preprocessor", preprocessor),
                    (
                        "regressor",
                        MLPRegressor(
                            hidden_layer_sizes=(50,), max_iter=500, random_state=42
                        ),
                    ),
                ]
            ),
        }

        best_model_name = None
        best_r2 = -float("inf")
        best_model = None

        for name, model in models.items():
            model.fit(X, y)
            preds = model.predict(X)
            mse = mean_squared_error(y, preds)
            r2 = r2_score(y, preds)
            print(f"Model: {name:<20} | RMSE: {np.sqrt(mse):.4f} | R2: {r2:.4f}")

            if r2 > best_r2:
                best_r2 = r2
                best_model_name = name
                best_model = model

        print(f"\nBest Model: {best_model_name} (R2: {best_r2:.4f})")

        model_filename = os.path.join(
            os.path.dirname(__file__), "models", f"{target}_model.joblib"
        )
        os.makedirs(os.path.dirname(model_filename), exist_ok=True)
        joblib.dump(
            {
                "model": best_model,
                "features": selected_features,
                "numeric_features": selected_numeric,
                "categorical_features": categorical_features,
            },
            model_filename,
        )
        print(f"Model saved to {model_filename}")


if __name__ == "__main__":
    main()
