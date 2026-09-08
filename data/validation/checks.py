"""Controles de calidad para series diarias de mercado y macroeconomía."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    count: int = 0


@dataclass
class QualityReport:
    rows: int
    columns: int
    first_date: str | None
    last_date: str | None
    issues: list[QualityIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def score(self) -> float:
        penalty = sum({"error": 35, "warning": 8, "info": 1}.get(issue.severity, 0) for issue in self.issues)
        return float(max(0, 100 - penalty))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["passed"] = self.passed
        payload["score"] = self.score
        return payload


def validate_market_data(
    frame: pd.DataFrame,
    min_rows: int = 1000,
    freshness_warning_days: int = 7,
    as_of: date | None = None,
) -> QualityReport:
    as_of = as_of or date.today()
    if not isinstance(frame.index, pd.DatetimeIndex):
        return QualityReport(
            len(frame),
            len(frame.columns),
            None,
            None,
            issues=[QualityIssue("error", "invalid_timestamp_index", "El índice debe ser DatetimeIndex.")],
        )
    first = frame.index.min().date().isoformat() if len(frame) else None
    last = frame.index.max().date().isoformat() if len(frame) else None
    report = QualityReport(len(frame), len(frame.columns), first, last)

    required = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        report.issues.append(QualityIssue("error", "missing_columns", f"Faltan columnas: {missing_columns}", len(missing_columns)))
        return report

    if len(frame) < min_rows:
        report.issues.append(QualityIssue("error", "insufficient_history", f"Solo hay {len(frame)} filas; se requieren al menos {min_rows}.", len(frame)))

    duplicate_count = int(frame.index.duplicated().sum())
    if duplicate_count:
        report.issues.append(QualityIssue("error", "duplicate_dates", "Hay fechas de mercado duplicadas.", duplicate_count))
    if not frame.index.is_monotonic_increasing:
        report.issues.append(QualityIssue("error", "unsorted_dates", "Las fechas no están ordenadas."))
    if frame.index.tz is not None:
        report.issues.append(QualityIssue("warning", "timezone_not_normalized", "El índice conserva timezone; se esperaba fecha de sesión sin zona."))
    long_gaps = int((frame.index.to_series().diff().dt.days > 7).sum())
    if long_gaps:
        report.issues.append(QualityIssue("warning", "calendar_gaps", "Hay intervalos superiores a siete días entre sesiones.", long_gaps))

    price_nulls = int(frame[required[:-1]].isna().any(axis=1).sum())
    if price_nulls:
        rate = price_nulls / max(len(frame), 1)
        severity = "error" if rate > 0.01 else "warning"
        report.issues.append(QualityIssue(severity, "missing_prices", f"{price_nulls} sesiones tienen precios faltantes ({rate:.2%}).", price_nulls))

    nonpositive = int((frame[["Open", "High", "Low", "Close", "Adj Close"]] <= 0).any(axis=1).sum())
    if nonpositive:
        report.issues.append(QualityIssue("error", "nonpositive_prices", "Se detectaron precios no positivos.", nonpositive))
    negative_volume = int((frame["Volume"] < 0).sum())
    if negative_volume:
        report.issues.append(QualityIssue("error", "negative_volume", "Se detectó volumen negativo.", negative_volume))

    incoherent = int(((frame["High"] < frame[["Open", "Close", "Low"]].max(axis=1)) | (frame["Low"] > frame[["Open", "Close", "High"]].min(axis=1))).sum())
    if incoherent:
        report.issues.append(QualityIssue("error", "ohlc_incoherent", "Hay sesiones que incumplen las relaciones OHLC.", incoherent))

    returns = np.log(frame["Adj Close"]).diff()
    extreme = int((returns.abs() > 0.30).sum())
    if extreme:
        report.issues.append(QualityIssue("warning", "extreme_returns", "Hay retornos diarios absolutos superiores a 30%; deben revisarse ajustes corporativos.", extreme))

    freshness_days = (as_of - frame.index.max().date()).days if len(frame) else 10_000
    report.metrics.update(
        {
            "duplicate_dates": duplicate_count,
            "missing_price_rows": price_nulls,
            "freshness_calendar_days": freshness_days,
            "extreme_return_rows": extreme,
            "market_sessions": len(frame),
            "calendar_gaps_over_7_days": long_gaps,
            "timezone": str(frame.index.tz) if frame.index.tz is not None else "session_date_naive",
        }
    )
    if freshness_days > freshness_warning_days:
        report.issues.append(QualityIssue("warning", "stale_data", f"La última sesión disponible tiene {freshness_days} días calendario de antigüedad."))

    macro_columns = [column for column in frame.columns if column.startswith("macro_") or column == "vix"]
    macro_null_rates = {column: float(frame[column].isna().mean()) for column in macro_columns}
    report.metrics["macro_null_rates"] = macro_null_rates
    high_nulls = [column for column, rate in macro_null_rates.items() if rate > 0.35]
    if high_nulls:
        report.issues.append(QualityIssue("warning", "macro_coverage", f"Cobertura insuficiente en: {high_nulls}.", len(high_nulls)))

    return report


def assert_usable(report: QualityReport) -> None:
    if not report.passed:
        details = "; ".join(issue.message for issue in report.issues if issue.severity == "error")
        raise ValueError(f"La validación de datos detuvo el pipeline: {details}")
