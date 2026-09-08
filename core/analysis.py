"""Orquestación completa y generación de snapshots auditables."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from backtesting.engine import BacktestResult, run_backtest
from backtesting.walk_forward import WalkForwardResult, run_walk_forward
from core.config import ProjectPaths, load_settings
from core.io import frame_fingerprint, materialize_duckdb, read_frame, write_frame, write_json, write_parquet
from data.features import build_features
from data.ingestion.pipeline import load_or_acquire
from decision.engine import explain_latest_signal
from decision.horizons import conditional_historical_outcomes


@dataclass
class AnalysisBundle:
    market: pd.DataFrame
    features: pd.DataFrame
    model_frame: pd.DataFrame
    decisions: pd.DataFrame
    backtest: BacktestResult
    fold_metrics: pd.DataFrame
    horizons: pd.DataFrame
    manifest: dict[str, Any]
    experiment: dict[str, Any]


def _source_fingerprint(paths: ProjectPaths) -> str:
    digest = hashlib.sha256()
    roots = [paths.root / name for name in ("core", "models", "decision", "backtesting", "data", "config")]
    files = sorted(file for root in roots for file in root.rglob("*") if file.suffix in {".py", ".yaml"})
    for file in files:
        digest.update(str(file.relative_to(paths.root)).encode("utf-8"))
        digest.update(file.read_bytes())
    return digest.hexdigest()


def _experiment_id(settings: dict[str, Any], data_fingerprint: str, code_fingerprint: str) -> str:
    stable = json.dumps(settings, sort_keys=True, default=str) + data_fingerprint + code_fingerprint
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:12]


def build_analysis(refresh: bool = False, settings: dict[str, Any] | None = None) -> AnalysisBundle:
    settings = settings or load_settings()
    paths = ProjectPaths()
    paths.ensure()
    market, manifest = load_or_acquire(refresh=refresh, settings=settings)
    features = build_features(market, settings["features"])
    write_frame(features, paths.features / "feature_store")

    quality_score = float(manifest["quality"]["score"])
    walk_forward: WalkForwardResult = run_walk_forward(features, settings, quality_score)
    backtest = run_backtest(
        walk_forward.decisions,
        float(settings["backtest"]["transaction_cost_bps"]),
        int(settings["backtest"]["annual_periods"]),
    )
    horizons = conditional_historical_outcomes(walk_forward.decisions)

    write_frame(walk_forward.model_frame, paths.processed / "oos_model_frame")
    write_frame(walk_forward.decisions, paths.processed / "oos_decisions")
    write_frame(walk_forward.fold_metrics, paths.processed / "walk_forward_metrics")
    write_frame(backtest.daily, paths.processed / "backtest_daily")
    write_frame(backtest.annual_returns, paths.processed / "annual_returns")
    write_frame(horizons, paths.processed / "conditional_horizons")
    write_parquet(market, paths.parquet / "market_daily.parquet")
    write_parquet(features, paths.parquet / "feature_store.parquet")
    write_parquet(walk_forward.decisions, paths.parquet / "oos_decisions.parquet")

    fingerprint = frame_fingerprint(market)
    code_fingerprint = _source_fingerprint(paths)
    experiment_id = _experiment_id(settings, fingerprint, code_fingerprint)
    latest = walk_forward.decisions.iloc[-1]
    current_columns = [
        "price",
        "opportunity_score",
        "risk_score",
        "confidence_score",
        "decision_state",
        "target_exposure",
        "regime_label",
        "regime_Bull",
        "regime_Neutral",
        "regime_Correction",
        "regime_Stress",
        "kalman_nis",
        "kalman_confidence",
        "change_risk",
        "egarch_volatility_forecast",
    ]
    experiment = {
        "experiment_id": experiment_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_version": settings["project"]["version"],
        "model_version": settings["project"]["version"],
        "code_fingerprint_sha256": code_fingerprint,
        "data_fingerprint_sha256": fingerprint,
        "data_first_date": manifest["first_date"],
        "data_last_date": manifest["last_date"],
        "configuration": settings,
        "current_state_date": latest.name.date().isoformat(),
        "current_state": {column: latest.get(column) for column in current_columns},
        "explanation": explain_latest_signal(walk_forward.decisions),
        "strategy_metrics": backtest.strategy_metrics,
        "benchmark_metrics": backtest.benchmark_metrics,
        "walk_forward_periods": [int(value) for value in walk_forward.fold_metrics.index],
        "lookahead_control": "Señal t aplicada a retorno t+1; HMM/EGARCH ajustados solo con train anterior al año de test.",
    }
    write_json(experiment, paths.processed / "experiment_latest.json")
    write_json(experiment, paths.processed / "experiments" / f"{experiment_id}.json")
    materialize_duckdb(
        {
            "market_daily": market,
            "feature_store": features,
            "oos_model_frame": walk_forward.model_frame,
            "oos_decisions": walk_forward.decisions,
            "backtest_daily": backtest.daily,
            "walk_forward_metrics": walk_forward.fold_metrics,
        },
        paths.duckdb,
    )
    return AnalysisBundle(
        market,
        features,
        walk_forward.model_frame,
        walk_forward.decisions,
        backtest,
        walk_forward.fold_metrics,
        horizons,
        manifest,
        experiment,
    )


def load_snapshot() -> AnalysisBundle:
    paths = ProjectPaths()
    required = [
        paths.processed / "market_daily.csv",
        paths.features / "feature_store.csv",
        paths.processed / "oos_model_frame.csv",
        paths.processed / "oos_decisions.csv",
        paths.processed / "backtest_daily.csv",
        paths.processed / "walk_forward_metrics.csv",
        paths.processed / "annual_returns.csv",
        paths.processed / "experiment_latest.json",
        paths.processed / "data_manifest.json",
    ]
    if not all(path.exists() for path in required):
        return build_analysis(refresh=False)
    with (paths.processed / "data_manifest.json").open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with (paths.processed / "experiment_latest.json").open("r", encoding="utf-8") as handle:
        experiment = json.load(handle)
    market = read_frame(paths.processed / "market_daily")
    features = read_frame(paths.features / "feature_store")
    model_frame = read_frame(paths.processed / "oos_model_frame")
    decisions = read_frame(paths.processed / "oos_decisions")
    daily = read_frame(paths.processed / "backtest_daily")
    fold_metrics = read_frame(paths.processed / "walk_forward_metrics")
    annual = read_frame(paths.processed / "annual_returns")
    try:
        horizons = read_frame(paths.processed / "conditional_horizons")
    except FileNotFoundError:
        horizons = conditional_historical_outcomes(decisions)
    backtest = BacktestResult(daily, experiment["strategy_metrics"], experiment["benchmark_metrics"], annual)
    return AnalysisBundle(market, features, model_frame, decisions, backtest, fold_metrics, horizons, manifest, experiment)
