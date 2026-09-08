"""Pipeline EOD: descarga, alinea causalmente, valida y persiste."""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import ProjectPaths, load_settings
from core.io import build_manifest, read_frame, write_frame, write_json
from core.logging import configure_logging
from data.providers.cboe import VIX_HISTORY_URL, download_vix
from data.providers.fred import align_as_available, download_fred_series, source_url as fred_source_url
from data.providers.yahoo import download_yahoo_daily, source_url as yahoo_source_url
from data.validation import assert_usable, validate_market_data


LOGGER = logging.getLogger(__name__)


def _is_cache_fresh(path: Path, hours: int) -> bool:
    csv_path = path.with_suffix(".csv")
    if not csv_path.exists():
        return False
    modified = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - modified).total_seconds() / 3600
    return age_hours <= hours


def _download_fred_bundle(settings: dict[str, Any], start: str, end: str) -> tuple[dict[str, pd.Series], list[str]]:
    definitions = settings["data"]["fred"]
    timeout = int(settings["data"]["request_timeout_seconds"])
    series: dict[str, pd.Series] = {}
    warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=min(6, len(definitions))) as pool:
        futures = {
            pool.submit(download_fred_series, spec["series"], start, end, timeout): (name, spec)
            for name, spec in definitions.items()
        }
        for future in as_completed(futures):
            name, spec = futures[future]
            try:
                series[name] = future.result()
            except Exception as exc:  # an optional macro series must not hide market data
                warnings.append(f"FRED {spec['series']} no disponible: {exc}")
                LOGGER.warning(warnings[-1])
    return series, warnings


def acquire_data(settings: dict[str, Any], paths: ProjectPaths | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = paths or ProjectPaths()
    paths.ensure()
    data_config = settings["data"]
    start = str(data_config["start_date"])
    end = str(data_config["end_date"])
    timeout = int(data_config["request_timeout_seconds"])

    LOGGER.info("Descargando %s desde %s hasta %s", data_config["market_symbol"], start, end)
    market = download_yahoo_daily(data_config["market_symbol"], start, end, timeout)
    write_frame(market, paths.raw / "spy_yahoo")
    base = market.drop(columns=["symbol"]).copy()

    warnings: list[str] = []
    sources = {
        "SPY": yahoo_source_url(data_config["market_symbol"]),
        "VIX": VIX_HISTORY_URL,
    }

    try:
        vix = download_vix(start, end, timeout)
        write_frame(vix, paths.raw / "vix_cboe")
        base = base.join(vix[["vix"]], how="left")
        base["vix"] = base["vix"].ffill(limit=3)
    except Exception as exc:
        warning = f"Cboe VIX falló; se usará Yahoo ^VIX: {exc}"
        LOGGER.warning(warning)
        warnings.append(warning)
        vix_yahoo = download_yahoo_daily("^VIX", start, end, timeout)
        base["vix"] = vix_yahoo["Adj Close"].reindex(base.index).ffill(limit=3)
        sources["VIX_fallback"] = yahoo_source_url("^VIX")

    try:
        reference = download_yahoo_daily(data_config["reference_symbol"], start, end, timeout)
        write_frame(reference, paths.raw / "spx_yahoo")
        base["spx_close"] = reference["Adj Close"].reindex(base.index)
        sources["SPX"] = yahoo_source_url(data_config["reference_symbol"])
    except Exception as exc:
        warning = f"SPX de referencia no disponible: {exc}"
        LOGGER.warning(warning)
        warnings.append(warning)

    expanded_start = (pd.Timestamp(start) - pd.Timedelta(days=500)).date().isoformat()
    fred_bundle, fred_warnings = _download_fred_bundle(settings, expanded_start, end)
    warnings.extend(fred_warnings)
    for name, definition in data_config["fred"].items():
        series_id = definition["series"]
        sources[f"FRED_{series_id}"] = fred_source_url(series_id)
        if name not in fred_bundle:
            base[f"macro_{name}"] = float("nan")
            continue
        source_series = fred_bundle[name]
        raw = source_series.to_frame(name=series_id)
        write_frame(raw, paths.raw / f"fred_{series_id.lower()}")
        base[f"macro_{name}"] = align_as_available(
            source_series,
            base.index,
            int(definition["lag_business_days"]),
        )

    base.index = pd.to_datetime(base.index).tz_localize(None)
    base.index.name = "date"
    base = base.sort_index()
    base = base.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    report = validate_market_data(
        base,
        min_rows=int(data_config["min_market_rows"]),
        freshness_warning_days=int(data_config["freshness_warning_days"]),
    )
    assert_usable(report)

    write_frame(base, paths.processed / "market_daily")
    manifest = build_manifest(base, sources, report.to_dict())
    manifest.update(
        {
            "warnings": warnings,
            "macro_vintage_mode": data_config["macro_vintage_mode"],
            "macro_vintage_safe": False,
            "availability_note": "Los rezagos evitan adelantar la publicación, pero FRED latest puede contener revisiones históricas.",
        }
    )
    write_json(manifest, paths.processed / "data_manifest.json")
    return base, manifest


def load_or_acquire(refresh: bool = False, settings: dict[str, Any] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    settings = settings or load_settings()
    paths = ProjectPaths()
    paths.ensure()
    base = paths.processed / "market_daily"
    if not refresh and _is_cache_fresh(base, int(settings["data"]["refresh_hours"])):
        frame = read_frame(base)
        manifest_path = paths.processed / "data_manifest.json"
        if manifest_path.exists():
            import json

            with manifest_path.open("r", encoding="utf-8") as handle:
                return frame, json.load(handle)
    return acquire_data(settings, paths)


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza datos EOD gratuitos de Decision Lab")
    parser.add_argument("--refresh", action="store_true", help="Ignora la caché local")
    args = parser.parse_args()
    paths = ProjectPaths()
    configure_logging(paths.logs / "ingestion.log")
    frame, manifest = load_or_acquire(refresh=args.refresh)
    print(f"OK: {len(frame):,} sesiones; última fecha {manifest['last_date']}; calidad {manifest['quality']['score']:.0f}/100")


if __name__ == "__main__":
    main()

