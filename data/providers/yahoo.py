"""Descarga diaria OHLCV desde el endpoint público Chart de Yahoo Finance."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import numpy as np
import pandas as pd

from .http import DataDownloadError, fetch_bytes


def _unix(day: str, add_day: bool = False) -> int:
    stamp = pd.Timestamp(day, tz="UTC")
    if add_day:
        stamp += pd.Timedelta(days=1)
    return int(stamp.timestamp())


def download_yahoo_daily(symbol: str, start: str, end: str, timeout: int = 45) -> pd.DataFrame:
    params = {
        "period1": _unix(start),
        "period2": _unix(end, add_day=True),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    errors: list[str] = []
    payload: bytes | None = None
    for host in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{quote(symbol, safe='')}?{urlencode(params)}"
        try:
            payload = fetch_bytes(url, timeout=timeout, attempts=2)
            break
        except DataDownloadError as exc:
            errors.append(str(exc))
    if payload is None:
        raise DataDownloadError("; ".join(errors))

    document = json.loads(payload)
    chart = document.get("chart", {})
    if chart.get("error"):
        raise DataDownloadError(f"Yahoo devolvió error para {symbol}: {chart['error']}")
    result = (chart.get("result") or [None])[0]
    if not result or not result.get("timestamp"):
        raise DataDownloadError(f"Yahoo no devolvió observaciones para {symbol}")

    quote_data = result["indicators"]["quote"][0]
    adjusted = (result["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    timestamps = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(None).normalize()
    frame = pd.DataFrame(
        {
            "Open": quote_data.get("open"),
            "High": quote_data.get("high"),
            "Low": quote_data.get("low"),
            "Close": quote_data.get("close"),
            "Adj Close": adjusted if adjusted is not None else quote_data.get("close"),
            "Volume": quote_data.get("volume"),
        },
        index=timestamps,
    )
    frame.index.name = "date"
    frame = frame.replace([np.inf, -np.inf], np.nan).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    frame = frame.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    frame["symbol"] = symbol
    return frame


def source_url(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{quote(symbol, safe='')}/history/"

