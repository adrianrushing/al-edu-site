import os
import joblib
import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException, Path, Request
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/predict", tags=["predict"])

_model_cache = {}


def get_model(target: str):
    if target not in _model_cache:
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "models", f"{target}_model.joblib"
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model for {target} not found at {model_path}")
        _model_cache[target] = joblib.load(model_path)
    return _model_cache[target]


@router.get("/baseline/{school_key}/{year}")
async def get_baseline(
    request: Request,
    school_key: int = Path(..., description="The school key"),
    year: int = Path(..., description="The academic year"),
):
    """
    Fetches the exact baseline features for a given school and year,
    formatted exactly as the models expect them.
    """
    pool = request.app.state.db_pool

    base_query = """
    SELECT
        o.ach_all,
        e.per_pupil_total_raw,
        e.nces_poverty,
        e.nces_freelunch,
        t.exp_rate,
        t.inexp_rate,
        i.nces_locale_type,
        CASE WHEN i.nces_charter THEN 1 ELSE 0 END as is_charter,
        CASE WHEN i.nces_magnet THEN 1 ELSE 0 END as is_magnet
    FROM core.dim_school_info i
    LEFT JOIN core.fact_school_outcomes_wide o
        ON o.school_key = i.school_key AND o.year = %s
    LEFT JOIN core.fact_edunomics e
        ON e.school_key = i.school_key AND e.year = %s
    LEFT JOIN core.fact_teacher_experience t
        ON t.school_key = i.school_key AND t.year = %s
       AND t.sub_population = 'All SubPopulation'
    WHERE i.school_key = %s
      AND i.school_year_start = %s
    LIMIT 1
    """

    defaults_query = """
    SELECT
        AVG(ach_all) AS ach_all,
        AVG(per_pupil_total_raw) AS per_pupil_total_raw,
        AVG(nces_poverty) AS nces_poverty,
        AVG(nces_freelunch) AS nces_freelunch,
        AVG(exp_rate) AS exp_rate,
        AVG(inexp_rate) AS inexp_rate
    FROM (
        SELECT o.ach_all,
               e.per_pupil_total_raw,
               e.nces_poverty,
               e.nces_freelunch,
               t.exp_rate,
               t.inexp_rate
        FROM core.dim_school_info i
        LEFT JOIN core.fact_school_outcomes_wide o
            ON o.school_key = i.school_key AND o.year = %s
        LEFT JOIN core.fact_edunomics e
            ON e.school_key = i.school_key AND e.year = %s
        LEFT JOIN core.fact_teacher_experience t
            ON t.school_key = i.school_key AND t.year = %s
           AND t.sub_population = 'All SubPopulation'
        WHERE i.school_year_start = %s
    ) stats
    """

    global_defaults_query = """
    SELECT
        AVG(ach_all) AS ach_all,
        AVG(per_pupil_total_raw) AS per_pupil_total_raw,
        AVG(nces_poverty) AS nces_poverty,
        AVG(nces_freelunch) AS nces_freelunch,
        AVG(exp_rate) AS exp_rate,
        AVG(inexp_rate) AS inexp_rate
    FROM (
        SELECT o.ach_all,
               e.per_pupil_total_raw,
               e.nces_poverty,
               e.nces_freelunch,
               t.exp_rate,
               t.inexp_rate
        FROM core.dim_school_info i
        LEFT JOIN core.fact_school_outcomes_wide o
            ON o.school_key = i.school_key
        LEFT JOIN core.fact_edunomics e
            ON e.school_key = i.school_key
        LEFT JOIN core.fact_teacher_experience t
            ON t.school_key = i.school_key
           AND t.sub_population = 'All SubPopulation'
    ) stats
    """

    demo_query = """
    SELECT race, demographic_count
    FROM core.fact_student_demographics
    WHERE school_key = %s AND year = %s
      AND ethnicity = 'All Ethnicity' AND race != 'All Race'
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch base stats
            cur.execute(base_query, (year, year, year, school_key, year))
            base_row = cur.fetchone()

            if not base_row:
                raise HTTPException(
                    status_code=404,
                    detail="Baseline data not found for this school and year.",
                )

            columns = [desc.name for desc in cur.description]
            baseline_data = dict(zip(columns, base_row))

            cur.execute(defaults_query, (year, year, year, year))
            defaults_row = cur.fetchone()
            default_columns = [desc.name for desc in cur.description]
            defaults = dict(zip(default_columns, defaults_row))

            cur.execute(global_defaults_query)
            global_defaults_row = cur.fetchone()
            global_defaults_columns = [desc.name for desc in cur.description]
            global_defaults = dict(zip(global_defaults_columns, global_defaults_row))

            numeric_keys = [
                "ach_all",
                "per_pupil_total_raw",
                "nces_poverty",
                "nces_freelunch",
                "exp_rate",
                "inexp_rate",
            ]
            for key in numeric_keys:
                if baseline_data.get(key) is None:
                    baseline_data[key] = defaults.get(key)
                if baseline_data.get(key) is None:
                    baseline_data[key] = global_defaults.get(key)

            if baseline_data.get("nces_locale_type") in (None, "", "Unknown"):
                baseline_data["nces_locale_type"] = "Suburb"

            # 2. Fetch and pivot demographics
            cur.execute(demo_query, (school_key, year))
            demo_rows = cur.fetchall()

            # Default all to 0.0
            races = [
                "American Indian/Alaska Native",
                "Asian",
                "Black or African American",
                "Native Hawaiian/Pacific Islander",
                "Two or More Races",
                "White",
            ]
            demo_counts = {r: 0.0 for r in races}

            for row in demo_rows:
                race = row[0]
                count = float(row[1]) if row[1] is not None else 0.0
                if race in demo_counts:
                    demo_counts[race] = count

            total_students = sum(demo_counts.values())

            for race in races:
                clean_name = "pct_" + race.lower().replace(" ", "_").replace("/", "_")
                pct = demo_counts[race] / total_students if total_students > 0 else 0.0
                baseline_data[clean_name] = float(pct)

            # Cast floats to ensure JSON serialization
            for k, v in baseline_data.items():
                if isinstance(v, (np.floating, float)):
                    baseline_data[k] = float(v)
                elif isinstance(v, (np.integer, int)):
                    baseline_data[k] = int(v)

            return baseline_data


class PredictRequest(BaseModel):
    # Core variables
    ach_all: Optional[float] = None
    per_pupil_total_raw: Optional[float] = None
    nces_poverty: Optional[float] = None
    nces_freelunch: Optional[float] = None
    exp_rate: Optional[float] = None
    inexp_rate: Optional[float] = None

    # Structural variables
    nces_locale_type: Optional[str] = Field(
        "City: Large", description="e.g. City: Large, Suburb: Large, Rural: Fringe"
    )
    is_charter: Optional[int] = Field(0, description="1 if charter, 0 otherwise")
    is_magnet: Optional[int] = Field(0, description="1 if magnet, 0 otherwise")

    # Demographics
    pct_american_indian_alaska_native: Optional[float] = 0.0
    pct_asian: Optional[float] = 0.0
    pct_black_or_african_american: Optional[float] = 0.0
    pct_native_hawaiian_pacific_islander: Optional[float] = 0.0
    pct_two_or_more_races: Optional[float] = 0.0
    pct_white: Optional[float] = 0.0


@router.post("/{target_variable}")
async def predict_variable(
    req: PredictRequest,
    target_variable: str = Path(..., description="The variable you want to predict"),
):
    valid_targets = [
        "ach_all",
        "per_pupil_total_raw",
        "nces_poverty",
        "nces_freelunch",
        "exp_rate",
        "inexp_rate",
    ]

    if target_variable not in valid_targets:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target variable. Must be one of {valid_targets}",
        )

    try:
        model_data = get_model(target_variable)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail=f"Model for {target_variable} could not be loaded."
        )

    model = model_data["model"]
    features = model_data["features"]

    input_dict = req.model_dump()

    # Construct a 1-row pandas DataFrame to pass to the pipeline
    # We must ensure all required features are present
    row_data = {}
    for f in features:
        val = input_dict.get(f)
        if val is None:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required feature for predicting {target_variable}: {f}",
            )
        row_data[f] = [val]

    df_new = pd.DataFrame(row_data)

    # Predict using the loaded pipeline (which handles imputation, scaling, one-hot encoding internally)
    prediction = model.predict(df_new)[0]

    regressor = (
        model.named_steps.get("regressor") if hasattr(model, "named_steps") else model
    )

    return {
        "target": target_variable,
        "predicted_value": float(prediction),
        "model_type": str(type(regressor).__name__),
        "features_used": features,
    }
