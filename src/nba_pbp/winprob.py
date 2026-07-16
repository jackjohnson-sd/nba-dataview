"""Stage 2 of the win-probability project: the model.

Every historical game becomes one training example, snapshotted at a
completion fraction (default 20%): pregame team-form features from
edge.team_form (as-of the game date, so nothing leaks), live features
from edge.live_reading_from_df, and the known outcome as the target.

Three nested feature sets keep the model honest:

- A  "pregame":      net-rating difference only
- B  "+margin":      A plus the live score margin
- full "+factors":   B plus the live four-factor differentials

A is the pregame baseline, B is the brutal in-game baseline that any
richer model must beat, and full is the hypothesis that HOW the first
stretch was played matters beyond the score. Models are deliberately
tiny — ridge regression for the final margin and L2-regularized
logistic regression for the win probability, both plain numpy — so
there's nothing to overfit with and no new dependencies.

Evaluation is strictly time-ordered: train on the earliest games, test
on the most recent, never shuffled.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from nba_pbp import client
from nba_pbp.edge import (
    league_history,
    live_reading_from_df,
    prepare_pbp,
    team_form,
    _season_for_game_id,
)

FEATURES = ["net_diff", "live_margin", "efg_d", "tov_d", "oreb_d", "ftr_d"]
FEATURE_SETS = {
    "A pregame": ["net_diff"],
    "B +margin": ["net_diff", "live_margin"],
    "full +factors": FEATURES,
}


def game_features(history: pd.DataFrame, home: str, away: str,
                  game_date: pd.Timestamp, pbp: pd.DataFrame,
                  fraction: float, n_games: int, half_life: float,
                  min_prior_games: int = 10) -> dict | None:
    """One game's feature row (home-minus-away orientation), or None if
    either team has too few prior games for a stable form estimate."""
    try:
        hf = team_form(history, home, game_date, n_games, half_life)
        af = team_form(history, away, game_date, n_games, half_life)
    except ValueError:
        return None
    if hf["games"] < min_prior_games or af["games"] < min_prior_games:
        return None
    live = live_reading_from_df(pbp, fraction)
    t = live["teams"]
    if home not in t or away not in t:
        return None
    return {
        "net_diff": hf["net_rtg"] - af["net_rtg"],
        "live_margin": live["score"][home] - live["score"][away],
        "efg_d": t[home]["efg"] - t[away]["efg"],
        "tov_d": t[home]["tov_pct"] - t[away]["tov_pct"],
        "oreb_d": t[home]["oreb_pct"] - t[away]["oreb_pct"],
        "ftr_d": t[home]["ftr"] - t[away]["ftr"],
    }


def build_dataset(seasons: list[str], fraction: float = 0.2,
                  n_games: int = 40, half_life: float = 15.0,
                  limit: int | None = None, fetch_delay: float = 0.6,
                  progress=None) -> pd.DataFrame:
    """One row per historical game: features at the cutoff plus the final
    outcome. Play-by-play is fetched once per game and disk-cached, so
    the builder is resumable; `fetch_delay` seconds of politeness apply
    only to actual network fetches. `limit` keeps the most recent N games
    per season (useful for a quick pipeline test)."""
    rows = []
    for season in seasons:
        history = league_history(season)
        home_games = history[history["MATCHUP"].str.contains(" vs. ")]
        home_games = home_games.sort_values("GAME_DATE")
        if limit:
            home_games = home_games.tail(limit)
        for _, g in home_games.iterrows():
            game_id = g["GAME_ID"]
            away = g["MATCHUP"].split(" vs. ")[-1]
            try:
                was_cached = client.has_cached_play_by_play(game_id)
                pbp = prepare_pbp(client.get_play_by_play_cached(game_id))
                if not was_cached and fetch_delay:
                    time.sleep(fetch_delay)
                feats = game_features(
                    history, g["TEAM_ABBREVIATION"], away, g["GAME_DATE"],
                    pbp, fraction, n_games, half_life,
                )
            except Exception as err:
                if progress:
                    progress(f"skip {game_id}: {err}")
                continue
            if feats is None:
                continue
            rows.append({
                "game_id": game_id,
                "date": g["GAME_DATE"].date().isoformat(),
                "home": g["TEAM_ABBREVIATION"],
                "away": away,
                **feats,
                "final_margin": int(g["PTS"] - g["OPP_PTS"]),
                "home_win": int(g["PTS"] > g["OPP_PTS"]),
            })
            if progress and len(rows) % 50 == 0:
                progress(f"{len(rows)} games processed (through {g['GAME_DATE'].date()})")
    return pd.DataFrame(rows)


# --- tiny numpy models -------------------------------------------------

def _standardize(X, mean=None, std=None):
    if mean is None:
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std == 0] = 1.0
    return (X - mean) / std, mean, std


def _ridge_fit(X, y, alpha=1.0):
    """Closed-form ridge on standardized X (intercept unpenalized)."""
    n, d = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    penalty = alpha * np.eye(d + 1)
    penalty[0, 0] = 0.0
    return np.linalg.solve(Xb.T @ Xb + penalty, Xb.T @ y)


def _logit_fit(X, y, alpha=1.0, iters=100):
    """L2-regularized logistic regression via IRLS on standardized X
    (intercept unpenalized)."""
    n, d = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    beta = np.zeros(d + 1)
    penalty = alpha * np.eye(d + 1)
    penalty[0, 0] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ beta))
        w = np.clip(p * (1 - p), 1e-6, None)
        grad = Xb.T @ (y - p) - penalty @ beta
        hess = (Xb * w[:, None]).T @ Xb + penalty
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def _predict_margin(beta, X):
    return np.hstack([np.ones((len(X), 1)), X]) @ beta


def _predict_prob(beta, X):
    return 1 / (1 + np.exp(-(np.hstack([np.ones((len(X), 1)), X]) @ beta)))


def train(dataset: pd.DataFrame, test_fraction: float = 0.2,
          alpha: float = 1.0) -> dict:
    """Fit every feature set on a strictly time-ordered split and report
    test metrics. Returns the full result bundle, including per-set
    coefficients and standardization, ready to serialize."""
    # a very early cutoff can produce NaN factors (e.g. zero FGA so far);
    # drop those few games rather than poison the fit
    df = dataset.dropna(subset=FEATURES).sort_values("date").reset_index(drop=True)
    n_test = max(1, int(len(df) * test_fraction))
    train_df, test_df = df.iloc[:-n_test], df.iloc[-n_test:]

    result = {
        "n_train": len(train_df), "n_test": len(test_df),
        "train_span": (train_df["date"].iloc[0], train_df["date"].iloc[-1]),
        "test_span": (test_df["date"].iloc[0], test_df["date"].iloc[-1]),
        "sets": {},
    }
    y_margin_tr = train_df["final_margin"].to_numpy(dtype=float)
    y_win_tr = train_df["home_win"].to_numpy(dtype=float)
    y_margin_te = test_df["final_margin"].to_numpy(dtype=float)
    y_win_te = test_df["home_win"].to_numpy(dtype=float)

    for name, cols in FEATURE_SETS.items():
        Xtr_raw = train_df[cols].to_numpy(dtype=float)
        Xte_raw = test_df[cols].to_numpy(dtype=float)
        Xtr, mean, std = _standardize(Xtr_raw)
        Xte, _, _ = _standardize(Xte_raw, mean, std)

        b_margin = _ridge_fit(Xtr, y_margin_tr, alpha)
        b_win = _logit_fit(Xtr, y_win_tr, alpha)

        pred_margin = _predict_margin(b_margin, Xte)
        prob = np.clip(_predict_prob(b_win, Xte), 1e-9, 1 - 1e-9)
        result["sets"][name] = {
            "features": cols,
            "mean": mean.tolist(), "std": std.tolist(),
            "beta_margin": b_margin.tolist(), "beta_win": b_win.tolist(),
            "margin_rmse": float(np.sqrt(((pred_margin - y_margin_te) ** 2).mean())),
            "margin_mae": float(np.abs(pred_margin - y_margin_te).mean()),
            "log_loss": float(-(y_win_te * np.log(prob)
                                + (1 - y_win_te) * np.log(1 - prob)).mean()),
            "brier": float(((prob - y_win_te) ** 2).mean()),
            "accuracy": float(((prob > 0.5) == y_win_te).mean()),
        }
    result["selected"] = min(result["sets"], key=lambda k: result["sets"][k]["log_loss"])
    return result


def save_model(result: dict, path: Path, fraction: float, seasons: list[str],
               n_games: int, half_life: float) -> None:
    payload = {
        "fraction": fraction, "seasons": seasons,
        "n_games": n_games, "half_life": half_life,
        **result,
    }
    path.write_text(json.dumps(payload, indent=2))


def predict_live(csv_path: Path, model_path: Path) -> dict:
    """Win probability and expected final margin for a live game CSV,
    using the saved model's selected feature set (and the baselines for
    context)."""
    model = json.loads(Path(model_path).read_text())
    raw = pd.read_csv(csv_path, usecols=["gameId"], dtype=str)
    game_id = raw.iloc[0, 0].zfill(10)
    history = league_history(_season_for_game_id(game_id))
    this_game = history[
        (history["GAME_ID"] == game_id) & history["MATCHUP"].str.contains(" vs. ")
    ]
    if this_game.empty:
        raise ValueError(f"game {game_id} not in season logs")
    g = this_game.iloc[0]
    home, away = g["TEAM_ABBREVIATION"], g["MATCHUP"].split(" vs. ")[-1]

    from nba_pbp.plusminus import _load_full_pbp
    feats = game_features(
        history, home, away, g["GAME_DATE"], _load_full_pbp(csv_path),
        model["fraction"], model["n_games"], model["half_life"],
    )
    if feats is None:
        raise ValueError("not enough prior games to build features")

    out = {"game_id": game_id, "home": home, "away": away,
           "fraction": model["fraction"], "features": feats, "sets": {}}
    for name, spec in model["sets"].items():
        X = np.array([[feats[c] for c in spec["features"]]], dtype=float)
        X = (X - np.array(spec["mean"])) / np.array(spec["std"])
        out["sets"][name] = {
            "win_prob": float(_predict_prob(np.array(spec["beta_win"]), X)[0]),
            "margin": float(_predict_margin(np.array(spec["beta_margin"]), X)[0]),
        }
    out["selected"] = model["selected"]
    return out
