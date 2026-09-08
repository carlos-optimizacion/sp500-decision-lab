"""Frecuencias históricas condicionadas; no son pronósticos deterministas."""

from __future__ import annotations

import pandas as pd


HORIZONS = {"1 mes": 21, "3 meses": 63, "6 meses": 126, "12 meses": 252, "3 años": 756}


def conditional_historical_outcomes(decisions: pd.DataFrame) -> pd.DataFrame:
    required = {"price", "opportunity_score", "regime_label"}
    if decisions.empty or not required.issubset(decisions.columns):
        return pd.DataFrame()
    latest = decisions.dropna(subset=["opportunity_score"]).iloc[-1]
    score = float(latest["opportunity_score"])
    regime = str(latest["regime_label"])
    base = decisions.copy()
    mask = (base["regime_label"] == regime) & (base["opportunity_score"].sub(score).abs() <= 12)
    if int(mask.sum()) < 25:
        mask = base["opportunity_score"].sub(score).abs() <= 20

    records = []
    for label, sessions in HORIZONS.items():
        forward = base["price"].shift(-sessions) / base["price"] - 1.0
        sample = forward[mask & forward.notna()]
        records.append(
            {
                "horizon": label,
                "sessions": sessions,
                "positive_frequency": float((sample > 0).mean()) if len(sample) else float("nan"),
                "median_return": float(sample.median()) if len(sample) else float("nan"),
                "p25_return": float(sample.quantile(0.25)) if len(sample) else float("nan"),
                "p75_return": float(sample.quantile(0.75)) if len(sample) else float("nan"),
                "observations": int(len(sample)),
                "effective_observations": int(max(1, round(len(sample) / max(1.0, sessions / 21.0)))) if len(sample) else 0,
                "condition": f"{regime}; Opportunity ±{12 if int(mask.sum()) >= 25 else 20} puntos",
            }
        )
    return pd.DataFrame(records).set_index("horizon")
