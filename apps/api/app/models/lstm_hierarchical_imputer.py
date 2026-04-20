from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine
from torch.utils.data import DataLoader, Dataset

try:
    from app.config import settings
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[4]
    api_root = repo_root / "apps" / "api"
    if str(api_root) not in sys.path:
        sys.path.append(str(api_root))
    from app.config import settings


ALL_GENDER = "All Gender"
ALL_ETHNICITY = "All Ethnicity"
ALL_RACE = "All Race"


@dataclass
class Config:
    table_name: str = "core.fact_student_demographics"
    output_csv: str = "apps/api/app/models/student_lstm_imputation_review.csv"
    seed: int = 42
    epochs: int = 12
    batch_size: int = 4096
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    hidden_size: int = 96
    num_layers: int = 2
    dropout: float = 0.2
    bidirectional: bool = True
    val_size: float = 0.1
    synth_mask_prob: float = 0.25
    synth_mask_min: float = 10.0
    synth_mask_max: float = 15.0
    max_reconcile_iter: int = 8
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def normalize_label(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def load_from_db(table_name: str) -> pd.DataFrame:
    sql = f"""
    SELECT
        school_key,
        year,
        grade,
        gender,
        ethnicity,
        race,
        sub_population,
        demographic_count,
        _created_at,
        _updated_at
    FROM {table_name}
    ORDER BY school_key, grade, gender, ethnicity, race, sub_population, year
    """
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in ["_created_at", "_updated_at"]:
        if c in out.columns:
            out = out.drop(columns=c)

    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out[out["year"].notna()].copy()
    out["year"] = out["year"].astype(np.int16)

    for c in ["grade", "gender", "ethnicity", "race", "sub_population"]:
        out[c] = normalize_label(out[c])

    out["demographic_count"] = pd.to_numeric(out["demographic_count"], errors="coerce")
    out["was_missing"] = out["demographic_count"].isna()

    for c in ["school_key", "grade", "gender", "ethnicity", "race", "sub_population"]:
        out[c] = out[c].astype("category")

    return out


def encode_categories(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict]]:
    out = df.copy()
    mappings: dict[str, dict] = {}
    cat_cols = ["school_key", "grade", "gender", "ethnicity", "race", "sub_population"]
    for col in cat_cols:
        cats = out[col].cat.categories
        mapping = {v: i + 1 for i, v in enumerate(cats)}
        mappings[col] = mapping
        out[f"{col}_id"] = out[col].map(mapping).astype(np.int32)
    return out, mappings


def build_sequences(df: pd.DataFrame, scaler: StandardScaler) -> dict:
    seq_keys = ["school_key", "gender", "ethnicity", "race", "sub_population"]

    # Prefer "All Grades" row when multiple grade rows exist for same seq-year.
    prep = df.copy()
    prep["_row_id"] = np.arange(len(prep), dtype=np.int64)
    prep["_is_all_grades"] = (prep["grade"].astype(str) == "All Grades").astype(np.int8)
    prep = prep.sort_values(
        by=seq_keys + ["year", "_is_all_grades", "_row_id"],
        ascending=[True, True, True, True, True, True, False, True],
        kind="mergesort",
    )
    prep = prep.drop_duplicates(subset=seq_keys + ["year"], keep="first").copy()
    prep = prep.drop(columns=["_is_all_grades", "_row_id"])

    seq_map = prep[seq_keys].drop_duplicates().reset_index(drop=True)
    seq_map["seq_id"] = np.arange(len(seq_map), dtype=np.int64)

    years = np.sort(prep["year"].unique())
    year_to_idx = {int(y): i for i, y in enumerate(years)}
    t_steps = len(years)

    work = prep.merge(seq_map, on=seq_keys, how="left")
    work["t_idx"] = work["year"].map(year_to_idx).astype(np.int16)

    n_seq = len(seq_map)
    value = np.zeros((n_seq, t_steps), dtype=np.float32)
    observed = np.zeros((n_seq, t_steps), dtype=np.float32)
    row_exists = np.zeros((n_seq, t_steps), dtype=np.float32)
    target_raw = np.zeros((n_seq, t_steps), dtype=np.float32)

    seq_ids = work["seq_id"].to_numpy(dtype=np.int64)
    t_idxs = work["t_idx"].to_numpy(dtype=np.int16)
    y = work["demographic_count"].to_numpy(dtype=np.float32)
    obs = (~np.isnan(y)).astype(np.float32)
    y_filled = np.nan_to_num(y, nan=0.0).astype(np.float32)

    row_exists[seq_ids, t_idxs] = 1.0
    observed[seq_ids, t_idxs] = np.maximum(observed[seq_ids, t_idxs], obs)
    target_raw[seq_ids, t_idxs] = y_filled

    obs_idx = np.where(obs > 0)[0]
    if obs_idx.size:
        scaled = (
            scaler.transform(y_filled[obs_idx].reshape(-1, 1)).astype(np.float32).ravel()
        )
        value[seq_ids[obs_idx], t_idxs[obs_idx]] = scaled

    static_cols = [
        "school_key_id",
        "gender_id",
        "ethnicity_id",
        "race_id",
        "sub_population_id",
    ]
    static_df = (
        work.drop_duplicates("seq_id")[["seq_id"] + static_cols]
        .set_index("seq_id")
        .sort_index()
    )

    grade_dyn = np.zeros((n_seq, t_steps), dtype=np.int32)
    grade_ids = work["grade_id"].to_numpy(dtype=np.int32)
    grade_dyn[seq_ids, t_idxs] = grade_ids

    return {
        "work": work,
        "seq_map": seq_map,
        "years": years,
        "value": value,
        "observed": observed,
        "row_exists": row_exists,
        "target_raw": target_raw,
        "static": {
            c: np.array(static_df[c].to_numpy(dtype=np.int32), copy=True)
            for c in static_cols
        },
        "grade_dyn": np.array(grade_dyn, copy=True),
        "seq_keys": seq_keys,
        "n_seq": n_seq,
        "t_steps": t_steps,
    }


class SequenceDataset(Dataset):
    def __init__(
        self, tensors: dict, seq_idx: np.ndarray, cfg: Config, train: bool = True
    ):
        self.cfg = cfg
        self.train = train
        self.value = tensors["value"][seq_idx]
        self.observed = tensors["observed"][seq_idx]
        self.row_exists = tensors["row_exists"][seq_idx]
        self.target_raw = tensors["target_raw"][seq_idx]
        self.static = {k: v[seq_idx] for k, v in tensors["static"].items()}
        self.grade_dyn = tensors["grade_dyn"][seq_idx]

    def __len__(self) -> int:
        return self.value.shape[0]

    def __getitem__(self, i: int) -> dict[str, torch.Tensor]:
        x_value = self.value[i].copy()
        x_obs = self.observed[i].copy()
        y_raw = self.target_raw[i].copy()
        exists = self.row_exists[i].copy()

        synth_mask = np.zeros_like(x_obs, dtype=np.float32)
        if self.train:
            eligible = (
                (x_obs > 0)
                & (y_raw >= self.cfg.synth_mask_min)
                & (y_raw <= self.cfg.synth_mask_max)
                & (exists > 0)
            )
            rnd = np.random.rand(*eligible.shape)
            chosen = eligible & (rnd < self.cfg.synth_mask_prob)
            synth_mask[chosen] = 1.0
            x_value[chosen] = 0.0
            x_obs[chosen] = 0.0

        sup_0_9 = ((self.observed[i] > 0) & (y_raw >= 0) & (y_raw <= 9)).astype(
            np.float32
        )

        sample: dict[str, torch.Tensor] = {
            "x_value": torch.from_numpy(x_value).float(),
            "x_obs": torch.from_numpy(x_obs).float(),
            "y_raw": torch.from_numpy(y_raw).float(),
            "exists": torch.from_numpy(exists).float(),
            "synth_mask": torch.from_numpy(synth_mask).float(),
            "sup_0_9": torch.from_numpy(sup_0_9).float(),
            "grade_dyn": torch.from_numpy(self.grade_dyn[i]).long(),
        }
        for k, arr in self.static.items():
            sample[k] = torch.tensor(arr[i], dtype=torch.long)
        return sample


class BiLSTMImputer(nn.Module):
    def __init__(self, vocab_sizes: dict[str, int], cfg: Config):
        super().__init__()
        self.emb = nn.ModuleDict()
        emb_sum = 0
        for k, v in vocab_sizes.items():
            dim = min(24, max(4, int(math.sqrt(v + 1))))
            self.emb[k] = nn.Embedding(v + 1, dim, padding_idx=0)
            emb_sum += dim

        in_dim = emb_sum + 2
        self.lstm = nn.LSTM(
            input_size=in_dim,
            hidden_size=cfg.hidden_size,
            num_layers=cfg.num_layers,
            dropout=cfg.dropout if cfg.num_layers > 1 else 0.0,
            batch_first=True,
            bidirectional=cfg.bidirectional,
        )
        out_dim = cfg.hidden_size * (2 if cfg.bidirectional else 1)
        self.recon_head = nn.Sequential(
            nn.Linear(out_dim, out_dim // 2),
            nn.ReLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(out_dim // 2, 1),
        )
        self.impute_head = nn.Sequential(
            nn.Linear(out_dim, out_dim // 2),
            nn.ReLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(out_dim // 2, 1),
            nn.Sigmoid(),
        )

    def forward(
        self, batch: dict[str, torch.Tensor]
    ) -> tuple[torch.Tensor, torch.Tensor]:
        bsz, t_steps = batch["x_value"].shape
        emb_tensors = []
        for k in self.emb:
            if batch[k].dim() == 2:
                e = self.emb[k](batch[k])
            else:
                e = self.emb[k](batch[k]).unsqueeze(1).expand(bsz, t_steps, -1)
            emb_tensors.append(e)
        x_num = torch.stack([batch["x_value"], batch["x_obs"]], dim=-1)
        x = torch.cat(emb_tensors + [x_num], dim=-1)
        h, _ = self.lstm(x)
        recon = self.recon_head(h).squeeze(-1)
        imp = self.impute_head(h).squeeze(-1) * 9.0
        return recon, imp


class CompositeLoss(nn.Module):
    def __init__(self, scaler: StandardScaler):
        super().__init__()
        self.mean = float(scaler.mean_[0])
        self.scale = float(max(scaler.scale_[0], 1e-8))

    def norm(self, y: torch.Tensor) -> torch.Tensor:
        return (y - self.mean) / self.scale

    def forward(
        self, recon: torch.Tensor, imp: torch.Tensor, batch: dict[str, torch.Tensor]
    ) -> torch.Tensor:
        y = batch["y_raw"]
        y_norm = self.norm(y)
        synth = batch["synth_mask"]
        sup_0_9 = batch["sup_0_9"]
        exists = batch["exists"]
        obs = batch["x_obs"]

        recon_denoise = ((recon - y_norm) ** 2 * synth).sum() / (synth.sum() + 1e-8)
        recon_stab = ((recon - y_norm) ** 2 * obs * exists).sum() / (
            (obs * exists).sum() + 1e-8
        )
        imp_fit = ((imp - y) ** 2 * sup_0_9).sum() / (sup_0_9.sum() + 1e-8)
        bound_pen = (
            (torch.relu(-imp) ** 2 + torch.relu(imp - 9.0) ** 2) * exists
        ).sum() / (exists.sum() + 1e-8)

        return (
            1.0 * (0.8 * recon_denoise + 0.2 * recon_stab)
            + 1.0 * imp_fit
            + 0.2 * bound_pen
        )


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: str,
    optimizer: torch.optim.Optimizer | None = None,
) -> float:
    train = optimizer is not None
    model.train(train)
    total_loss = 0.0
    total_items = 0
    for batch in loader:
        for k in batch:
            batch[k] = batch[k].to(device)
        recon, imp = model(batch)
        loss = criterion(recon, imp, batch)
        if train:
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        bsz = batch["x_value"].shape[0]
        total_loss += float(loss.item()) * bsz
        total_items += bsz
    return total_loss / max(total_items, 1)


@torch.no_grad()
def infer_all(model: nn.Module, tensors: dict, device: str) -> np.ndarray:
    model.eval()
    n_seq = tensors["n_seq"]
    t_steps = tensors["t_steps"]
    out = np.zeros((n_seq, t_steps), dtype=np.float32)
    chunk = 50000
    for start in range(0, n_seq, chunk):
        end = min(n_seq, start + chunk)
        batch: dict[str, torch.Tensor] = {
            "x_value": torch.from_numpy(
                np.ascontiguousarray(tensors["value"][start:end]).copy()
            )
            .float()
            .to(device),
            "x_obs": torch.from_numpy(
                np.ascontiguousarray(tensors["observed"][start:end]).copy()
            )
            .float()
            .to(device),
            "grade_dyn": torch.from_numpy(
                np.ascontiguousarray(tensors["grade_dyn"][start:end]).copy()
            )
            .long()
            .to(device),
        }
        for k, arr in tensors["static"].items():
            batch[k] = (
                torch.from_numpy(np.ascontiguousarray(arr[start:end]).copy())
                .long()
                .to(device)
            )
        _, imp = model(batch)
        out[start:end] = imp.cpu().numpy().astype(np.float32)
    return out


def bounded_integer_projection(
    targets: np.ndarray,
    lowers: np.ndarray,
    uppers: np.ndarray,
    required_sum: int,
) -> tuple[bool, np.ndarray]:
    base = lowers.astype(int)
    cap = (uppers - lowers).astype(int)
    residual = required_sum - int(base.sum())
    max_resid = int(cap.sum())
    if residual < 0 or residual > max_resid:
        return False, base

    n = len(targets)
    inf = 1e18
    dp = np.full((n + 1, max_resid + 1), inf, dtype=np.float64)
    choice = np.full((n + 1, max_resid + 1), -1, dtype=np.int16)
    dp[0, 0] = 0.0
    centered = targets - lowers

    for i in range(1, n + 1):
        c = int(cap[i - 1])
        t = float(centered[i - 1])
        for s in range(0, max_resid + 1):
            best = inf
            best_v = -1
            max_v = min(c, s)
            for v in range(0, max_v + 1):
                prev = dp[i - 1, s - v]
                if prev >= inf:
                    continue
                cost = prev + (v - t) * (v - t)
                if cost < best:
                    best = cost
                    best_v = v
            dp[i, s] = best
            choice[i, s] = best_v

    if choice[n, residual] < 0:
        return False, base

    assign = np.zeros(n, dtype=int)
    s = residual
    for i in range(n, 0, -1):
        v = int(choice[i, s])
        assign[i - 1] = v
        s -= v
    return True, base + assign


def reconcile_single_equation(
    parent_value: float,
    child_values: np.ndarray,
    parent_target: float,
    child_targets: np.ndarray,
    parent_observed: bool,
    child_observed: np.ndarray,
) -> tuple[bool, int, np.ndarray]:
    if parent_observed:
        parent_low = parent_high = int(round(parent_value))
    else:
        parent_low, parent_high = 0, 9

    child_lows = np.where(child_observed, np.rint(child_values).astype(int), 0)
    child_highs = np.where(child_observed, np.rint(child_values).astype(int), 9)

    best_obj = float("inf")
    best_parent = int(round(parent_value))
    best_children = np.rint(child_values).astype(int)
    feasible_any = False

    for candidate_parent in range(parent_low, parent_high + 1):
        ok, cand_children = bounded_integer_projection(
            targets=child_targets,
            lowers=child_lows,
            uppers=child_highs,
            required_sum=candidate_parent,
        )
        if not ok:
            continue
        feasible_any = True
        obj = float(
            (candidate_parent - parent_target) ** 2
            + np.sum((cand_children - child_targets) ** 2)
        )
        if obj < best_obj:
            best_obj = obj
            best_parent = candidate_parent
            best_children = cand_children

    return feasible_any, best_parent, best_children


def reconcile_dimension(
    df: pd.DataFrame,
    dim_col: str,
    all_label: str,
    context_cols: list[str],
    value_col: str,
    pred_col: str,
) -> tuple[pd.DataFrame, set[int], set[int]]:
    out = df
    adjusted_idx: set[int] = set()
    infeasible_idx: set[int] = set()

    grouped = out.groupby(context_cols, sort=False, observed=True)
    for _, idx in grouped.groups.items():
        loc = out.loc[idx]
        parent = loc[loc[dim_col] == all_label]
        children = loc[loc[dim_col] != all_label]
        if parent.empty or children.empty:
            continue

        parent_i = int(parent.index[0])
        child_i = children.index.to_numpy(dtype=int)

        parent_value = float(out.at[parent_i, value_col])
        parent_target = float(out.at[parent_i, pred_col])
        child_values = out.loc[child_i, value_col].to_numpy(dtype=float)
        child_targets = out.loc[child_i, pred_col].to_numpy(dtype=float)

        parent_observed = bool(not out.at[parent_i, "was_missing"])
        child_observed = (~out.loc[child_i, "was_missing"]).to_numpy(dtype=bool)

        feasible, p_new, c_new = reconcile_single_equation(
            parent_value=parent_value,
            child_values=child_values,
            parent_target=parent_target,
            child_targets=child_targets,
            parent_observed=parent_observed,
            child_observed=child_observed,
        )

        if not feasible:
            infeasible_idx.add(parent_i)
            infeasible_idx.update(child_i.tolist())
            continue

        if out.at[parent_i, "was_missing"]:
            old = float(out.at[parent_i, value_col])
            out.at[parent_i, value_col] = float(p_new)
            if old != float(p_new):
                adjusted_idx.add(parent_i)

        for j, new_v in zip(child_i, c_new, strict=False):
            if bool(out.at[j, "was_missing"]):
                old = float(out.at[j, value_col])
                out.at[j, value_col] = float(new_v)
                if old != float(new_v):
                    adjusted_idx.add(int(j))

    return out, adjusted_idx, infeasible_idx


def hierarchical_reconcile(
    df: pd.DataFrame, cfg: Config
) -> tuple[pd.DataFrame, set[int], set[int]]:
    out = df.copy()
    all_adjusted: set[int] = set()
    all_infeasible: set[int] = set()

    for _ in range(cfg.max_reconcile_iter):
        pass_adjusted: set[int] = set()

        out, a1, i1 = reconcile_dimension(
            out,
            dim_col="gender",
            all_label=ALL_GENDER,
            context_cols=[
                "school_key",
                "year",
                "grade",
                "sub_population",
                "ethnicity",
                "race",
            ],
            value_col="reconciled_count",
            pred_col="lstm_pred_count",
        )
        out, a2, i2 = reconcile_dimension(
            out,
            dim_col="ethnicity",
            all_label=ALL_ETHNICITY,
            context_cols=[
                "school_key",
                "year",
                "grade",
                "sub_population",
                "gender",
                "race",
            ],
            value_col="reconciled_count",
            pred_col="lstm_pred_count",
        )
        out, a3, i3 = reconcile_dimension(
            out,
            dim_col="race",
            all_label=ALL_RACE,
            context_cols=[
                "school_key",
                "year",
                "grade",
                "sub_population",
                "gender",
                "ethnicity",
            ],
            value_col="reconciled_count",
            pred_col="lstm_pred_count",
        )

        pass_adjusted.update(a1)
        pass_adjusted.update(a2)
        pass_adjusted.update(a3)
        all_infeasible.update(i1)
        all_infeasible.update(i2)
        all_infeasible.update(i3)
        all_adjusted.update(pass_adjusted)

        if not pass_adjusted:
            break

    return out, all_adjusted, all_infeasible


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BiLSTM hierarchical imputer from DB -> CSV"
    )
    parser.add_argument("--table", default=Config.table_name)
    parser.add_argument("--output-csv", default=Config.output_csv)
    parser.add_argument("--epochs", type=int, default=Config.epochs)
    parser.add_argument("--batch-size", type=int, default=Config.batch_size)
    parser.add_argument("--seed", type=int, default=Config.seed)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        table_name=args.table,
        output_csv=args.output_csv,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
    )

    set_seed(cfg.seed)
    print(f"Loading source table: {cfg.table_name}")
    raw = load_from_db(cfg.table_name)
    df = preprocess(raw)
    df_enc, mappings = encode_categories(df)

    observed = df_enc.loc[~df_enc["was_missing"], "demographic_count"].to_numpy(
        dtype=np.float32
    )
    scaler = StandardScaler().fit(observed.reshape(-1, 1))

    tensors = build_sequences(df_enc, scaler)
    n_seq = tensors["n_seq"]
    print(
        f"Rows: {len(df_enc):,} | Model rows (seq-year): {len(tensors['work']):,} | Sequences: {n_seq:,} | Time steps: {tensors['t_steps']}"
    )

    train_idx, val_idx = train_test_split(
        np.arange(n_seq), test_size=cfg.val_size, random_state=cfg.seed
    )

    train_ds = SequenceDataset(tensors, train_idx, cfg, train=True)
    val_ds = SequenceDataset(tensors, val_idx, cfg, train=False)

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=2,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=cfg.batch_size, shuffle=False, num_workers=2, pin_memory=True
    )

    vocab_sizes = {
        "school_key_id": max(mappings["school_key"].values(), default=0),
        "grade_dyn": max(mappings["grade"].values(), default=0),
        "gender_id": max(mappings["gender"].values(), default=0),
        "ethnicity_id": max(mappings["ethnicity"].values(), default=0),
        "race_id": max(mappings["race"].values(), default=0),
        "sub_population_id": max(mappings["sub_population"].values(), default=0),
    }

    model = BiLSTMImputer(vocab_sizes, cfg).to(cfg.device)
    criterion = CompositeLoss(scaler)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay
    )

    best_val = float("inf")
    best_state: dict | None = None
    print(f"Training on device: {cfg.device}")
    for epoch in range(1, cfg.epochs + 1):
        tr_loss = run_epoch(model, train_loader, criterion, cfg.device, optimizer)
        va_loss = run_epoch(model, val_loader, criterion, cfg.device)
        print(f"Epoch {epoch:02d}/{cfg.epochs} | train={tr_loss:.6f} | val={va_loss:.6f}")
        if va_loss < best_val:
            best_val = va_loss
            best_state = {
                k: v.detach().cpu().clone() for k, v in model.state_dict().items()
            }

    if best_state is not None:
        model.load_state_dict(best_state)

    pred = infer_all(model, tensors, cfg.device)

    years = tensors["years"]
    year_to_idx = {int(y): i for i, y in enumerate(years)}
    out = tensors["work"].copy()
    out["t_idx"] = out["year"].map(year_to_idx).astype(np.int16)
    seq_ids = out["seq_id"].to_numpy(dtype=np.int64)
    t_idxs = out["t_idx"].to_numpy(dtype=np.int16)
    out["lstm_pred_float"] = pred[seq_ids, t_idxs]

    out["original_demographic_count"] = out["demographic_count"]
    out["lstm_pred_count"] = np.clip(
        np.round(out["lstm_pred_float"].fillna(0.0)), 0, 9
    ).astype(np.int16)
    out["reconciled_count"] = out["original_demographic_count"]
    miss_mask = out["was_missing"]
    out.loc[miss_mask, "reconciled_count"] = out.loc[miss_mask, "lstm_pred_count"].astype(
        float
    )

    out, adjusted_idx, infeasible_idx = hierarchical_reconcile(out, cfg)

    out["hierarchy_adjusted"] = False
    if adjusted_idx:
        out.loc[list(adjusted_idx), "hierarchy_adjusted"] = True

    out["hierarchy_infeasible"] = False
    if infeasible_idx:
        out.loc[list(infeasible_idx), "hierarchy_infeasible"] = True

    out["final_demographic_count"] = out["original_demographic_count"]
    out.loc[miss_mask, "final_demographic_count"] = np.clip(
        np.round(out.loc[miss_mask, "reconciled_count"]), 0, 9
    ).astype(np.int16)

    export_cols = [
        "school_key",
        "year",
        "grade",
        "gender",
        "ethnicity",
        "race",
        "sub_population",
        "original_demographic_count",
        "lstm_pred_count",
        "reconciled_count",
        "final_demographic_count",
        "was_missing",
        "hierarchy_adjusted",
        "hierarchy_infeasible",
    ]

    out_csv_path = Path(cfg.output_csv)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    out[export_cols].to_csv(out_csv_path, index=False)

    total_missing = int(out["was_missing"].sum())
    total_adjusted = int(out["hierarchy_adjusted"].sum())
    total_infeasible = int(out["hierarchy_infeasible"].sum())
    print(f"Wrote review CSV: {out_csv_path}")
    print(f"Missing rows imputed: {total_missing:,}")
    print(f"Rows adjusted by hierarchy reconciliation: {total_adjusted:,}")
    print(f"Rows in infeasible hierarchy groups: {total_infeasible:,}")


if __name__ == "__main__":
    main()
