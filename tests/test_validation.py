from __future__ import annotations

import pandas as pd

from data.providers.fred import align_as_available
from data.validation import validate_market_data


def test_validation_rejects_duplicate_dates(market_frame):
    duplicated = pd.concat([market_frame, market_frame.iloc[[0]]]).sort_index()
    report = validate_market_data(duplicated, min_rows=100)
    assert not report.passed
    assert any(issue.code == "duplicate_dates" for issue in report.issues)


def test_fred_alignment_respects_release_lag():
    source = pd.Series([5.0], index=pd.DatetimeIndex(["2025-01-02"]))
    market_index = pd.bdate_range("2025-01-02", periods=5)
    aligned = align_as_available(source, market_index, lag_business_days=2)
    assert pd.isna(aligned.iloc[0]) and pd.isna(aligned.iloc[1])
    assert aligned.iloc[2] == 5.0

