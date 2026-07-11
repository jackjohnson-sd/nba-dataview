"""Save play-by-play / game listing data to disk."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_dataframe(df: pd.DataFrame, path: Path, fmt: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "json":
        df.to_json(path, orient="records", indent=2)
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    return path
