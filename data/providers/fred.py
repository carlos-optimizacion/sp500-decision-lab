"""Series macroeconómicas oficiales descargadas de FRED sin API key."""

from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode

import pandas as pd
from pandas.tseries.offsets import BDay

from .http import fetch_bytes


FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def download_fred_series(series_id: str, start: str, end: str, timeout: int = 45) -> pd.Series:
    query = urlencode({"id": series_id, "cosd": start, "coed": end})
    raw = fetch_bytes(f"{FRED_CSV_URL}?{query}", timeout=timeout)
    frame = pd.read_csv(BytesIO(raw))
    date_column = frame.columns[0]
    value_column = frame.columns[1]
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    series = frame.dropna(subset=[date_column]).set_index(date_column)[value_column].sort_index()
    series.index.name = "date"
    series.name = series_id
    return series.loc[pd.Timestamp(start) : pd.Timestamp(end)]


def align_as_available(series: pd.Series, market_index: pd.DatetimeIndex, lag_business_days: int) -> pd.Series:
    """Hace visible cada observación después de un rezago de publicación conservador."""

    available = series.dropna().copy()
    available.index = pd.DatetimeIndex(available.index) + BDay(int(lag_business_days))
    available = available[~available.index.duplicated(keep="last")].sort_index()
    union = available.index.union(market_index).sort_values()
    aligned = available.reindex(union).ffill().reindex(market_index)
    aligned.index.name = "date"
    return aligned


def source_url(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/series/{series_id}"

