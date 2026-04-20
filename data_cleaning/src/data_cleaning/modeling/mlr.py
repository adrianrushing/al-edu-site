from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl
from sklearn.linear_model import LassoCV, LinearRegression
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class ModelResult:
    target_name: str
    feature_names: list[str]
    selected_features: list[str]
    cv_metrics: dict[str, dict[str, float]]
    fold_details: list[dict[str, Any]]
    feature_selection_freq: dict[str, float]
    sklearn_model: LinearRegression
    statsmodels_summary: str
    statsmodels_results: Any | None = None


def _prepare_xy(
    df: pl.DataFrame,
    feature_cols: list[str],
    target_col: str,
) -> tuple[np.ndarray, np.ndarray, list[str], pl.DataFrame]:
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataframe.")

    target_non_null = df.filter(pl.col(target_col).is_not_null())
    available_features = [
        c
        for c in feature_cols
        if c in target_non_null.columns
        and target_non_null[c].null_count() < target_non_null.height
    ]

    if len(available_features) == 0:
        raise ValueError(
            f"No feature columns found in dataframe. Requested: {feature_cols}"
        )

    clean = target_non_null.select(available_features + [target_col]).drop_nulls()
    if clean.height == 0:
        raise ValueError(
            f"No complete rows after dropping nulls for target '{target_col}'."
        )
    X = clean.select(available_features).to_numpy()
    y = clean[target_col].to_numpy()
    return X, y, available_features, clean


def _run_cv(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    cv_splits: int = 5,
    random_state: int = 42,
) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], dict[str, float]]:
    kf = KFold(n_splits=cv_splits, shuffle=True, random_state=random_state)
    fold_details: list[dict[str, Any]] = []
    r2_list: list[float] = []
    rmse_list: list[float] = []
    mae_list: list[float] = []
    selection_counts: dict[str, int] = {f: 0 for f in feature_names}

    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        scaler = StandardScaler()
        X_train_sc = scaler.fit_transform(X_train)
        X_val_sc = scaler.transform(X_val)

        lasso = LassoCV(cv=5, random_state=random_state, max_iter=10000)
        lasso.fit(X_train_sc, y_train)

        selected_mask = np.abs(lasso.coef_) > 1e-10
        selected_in_fold = [
            f for f, s in zip(feature_names, selected_mask, strict=False) if s
        ]
        for f in selected_in_fold:
            selection_counts[f] += 1

        if len(selected_in_fold) == 0:
            logger.warning(
                "Fold %d: LASSO selected zero features; skipping fold.", fold_idx
            )
            continue

        X_train_sel = X_train_sc[:, selected_mask]
        X_val_sel = X_val_sc[:, selected_mask]

        lr = LinearRegression()
        lr.fit(X_train_sel, y_train)
        y_pred = lr.predict(X_val_sel)

        r2 = float(np.corrcoef(y_val, y_pred)[0, 1] ** 2) if len(y_val) > 1 else 0.0
        rmse = float(np.sqrt(np.mean((y_val - y_pred) ** 2)))
        mae = float(np.mean(np.abs(y_val - y_pred)))

        r2_list.append(r2)
        rmse_list.append(rmse)
        mae_list.append(mae)

        fold_details.append(
            {
                "fold": fold_idx,
                "r2": r2,
                "rmse": rmse,
                "mae": mae,
                "selected_features": selected_in_fold,
                "n_selected": len(selected_in_fold),
                "lasso_alpha": float(lasso.alpha_),
            }
        )

    n_folds = max(len(fold_details), 1)
    cv_metrics = {
        "r2": {
            "mean": float(np.mean(r2_list)) if r2_list else 0.0,
            "std": float(np.std(r2_list)) if r2_list else 0.0,
        },
        "rmse": {
            "mean": float(np.mean(rmse_list)) if rmse_list else 0.0,
            "std": float(np.std(rmse_list)) if rmse_list else 0.0,
        },
        "mae": {
            "mean": float(np.mean(mae_list)) if mae_list else 0.0,
            "std": float(np.std(mae_list)) if mae_list else 0.0,
        },
    }
    feature_selection_freq = {f: count / n_folds for f, count in selection_counts.items()}
    return cv_metrics, fold_details, feature_selection_freq


def _fit_final_model(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
) -> tuple[LinearRegression, list[str], StandardScaler]:
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    lasso = LassoCV(cv=5, random_state=42, max_iter=10000)
    lasso.fit(X_sc, y)

    selected_mask = np.abs(lasso.coef_) > 1e-10
    selected_features = [
        f for f, s in zip(feature_names, selected_mask, strict=False) if s
    ]

    if len(selected_features) == 0:
        logger.warning("LASSO selected zero features on full data; using all features.")
        selected_features = list(feature_names)
        selected_mask = np.ones(len(feature_names), dtype=bool)

    lr = LinearRegression()
    lr.fit(X_sc[:, selected_mask], y)
    return lr, selected_features, scaler


def _build_statsmodels_summary(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    selected_features: list[str],
    scaler: StandardScaler,
) -> str:
    try:
        import statsmodels.api as sm
    except ImportError:
        return "statsmodels not installed; summary unavailable."

    sel_idx = [feature_names.index(f) for f in selected_features if f in feature_names]
    X_sel = X[:, sel_idx]
    X_sel_sc = StandardScaler().fit_transform(X_sel)
    X_sm = sm.add_constant(X_sel_sc)

    model = sm.OLS(y, X_sm).fit()
    return model.summary().as_text()


def _train_model(
    df: pl.DataFrame,
    feature_cols: list[str],
    target_col: str,
    target_name: str,
    cv_splits: int = 5,
    random_state: int = 42,
) -> ModelResult:
    X, y, available_features, clean_df = _prepare_xy(df, feature_cols, target_col)

    if clean_df.height < cv_splits * 5:
        raise ValueError(
            f"Too few complete rows ({clean_df.height}) for {cv_splits}-fold CV. "
            f"Need at least {cv_splits * 5}."
        )

    cv_metrics, fold_details, feature_selection_freq = _run_cv(
        X, y, available_features, cv_splits=cv_splits, random_state=random_state
    )

    lr, selected_features, scaler = _fit_final_model(X, y, available_features)
    sm_summary = _build_statsmodels_summary(
        X, y, available_features, selected_features, scaler
    )

    return ModelResult(
        target_name=target_name,
        feature_names=available_features,
        selected_features=selected_features,
        cv_metrics=cv_metrics,
        fold_details=fold_details,
        feature_selection_freq=feature_selection_freq,
        sklearn_model=lr,
        statsmodels_summary=sm_summary,
    )


def train_achievement_model(
    df: pl.DataFrame,
    feature_cols: list[str] | None = None,
    cv_splits: int = 5,
    random_state: int = 42,
) -> ModelResult:
    if feature_cols is None:
        feature_cols = [
            "student_diversity_index",
            "teacher_diversity_index",
            "teacher_exp_pct",
            "teacher_effectiveness_score",
            "coi",
        ]
    return _train_model(
        df, feature_cols, "ach_all", "achievement", cv_splits, random_state
    )


def train_funding_model(
    df: pl.DataFrame,
    feature_cols: list[str] | None = None,
    cv_splits: int = 5,
    random_state: int = 42,
) -> ModelResult:
    if feature_cols is None:
        feature_cols = [
            "student_diversity_index",
            "teacher_diversity_index",
            "teacher_exp_pct",
            "teacher_effectiveness_score",
            "coi",
        ]
    return _train_model(
        df, feature_cols, "per_pupil_total_k", "funding", cv_splits, random_state
    )
