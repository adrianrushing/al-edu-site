import os
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Path
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

    return {
        "target": target_variable,
        "predicted_value": float(prediction),
        "model_type": str(type(model.named_steps["regressor"]).__name__),
        "features_used": features,
    }
