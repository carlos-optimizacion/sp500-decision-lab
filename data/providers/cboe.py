"""Serie oficial histórica del índice VIX publicada por Cboe."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from .http import fetch_bytes


VIX_HISTORY_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"


def download_vix(start: str, end: str, timeout: int = 45) -> pd.DataFrame:
    raw = fetch_bytes(VIX_HISTORY_URL, timeout=timeout)
    frame = pd.read_csv(BytesIO(raw))
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    frame["date"] = pd.to_datetime(frame["date"], format="%m/%d/%Y", errors="coerce")
    frame = frame.dropna(subset=["date"]).set_index("date").sort_index()
    frame.index.name = "date"
    frame = frame.rename(columns={"open": "vix_open", "high": "vix_high", "low": "vix_low", "close": "vix"})
    for column in ("vix_open", "vix_high", "vix_low", "vix"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.loc[pd.Timestamp(start) : pd.Timestamp(end)]

