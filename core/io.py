"""Persistencia con Parquet/DuckDB y degradación explícita a CSV."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def frame_fingerprint(frame: pd.DataFrame) -> str:
    payload = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    return hashlib.sha256(payload).hexdigest()


def write_frame(frame: pd.DataFrame, base_path: Path) -> dict[str, str]:
    """Escribe CSV siempre y Parquet cuando pyarrow está disponible."""

    base_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = base_path.with_suffix(".csv")
    index_label = "date" if isinstance(frame.index, pd.DatetimeIndex) else (frame.index.name or "index")
    frame.to_csv(csv_path, index=True, index_label=index_label)
    outputs = {"csv": str(csv_path)}
    try:
        parquet_path = base_path.with_suffix(".parquet")
        frame.to_parquet(parquet_path, index=True)
        outputs["parquet"] = str(parquet_path)
    except (ImportError, ModuleNotFoundError):
        outputs["parquet"] = "unavailable: install pyarrow"
    return outputs


def write_parquet(frame: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=True)
        return str(path)
    except (ImportError, ModuleNotFoundError):
        return "unavailable: install pyarrow"


def read_frame(base_path: Path) -> pd.DataFrame:
    parquet_path = base_path.with_suffix(".parquet")
    csv_path = base_path.with_suffix(".csv")
    if parquet_path.exists():
        try:
            frame = pd.read_parquet(parquet_path)
            if frame.index.name == "date":
                frame.index = pd.to_datetime(frame.index)
            return frame
        except (ImportError, ModuleNotFoundError):
            pass
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe snapshot para {base_path}")
    header = pd.read_csv(csv_path, nrows=0).columns[0]
    if header == "date":
        frame = pd.read_csv(csv_path, index_col=header, parse_dates=[header])
    else:
        frame = pd.read_csv(csv_path, index_col=header)
    return frame


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)


def build_manifest(frame: pd.DataFrame, sources: dict[str, str], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "first_date": frame.index.min().date().isoformat() if len(frame) else None,
        "last_date": frame.index.max().date().isoformat() if len(frame) else None,
        "fingerprint_sha256": frame_fingerprint(frame),
        "sources": sources,
        "quality": quality,
    }


def materialize_duckdb(tables: dict[str, pd.DataFrame], database_path: Path) -> str:
    """Crea tablas locales consultables; no bloquea si DuckDB no está instalado."""

    try:
        import duckdb
    except (ImportError, ModuleNotFoundError):
        return "unavailable: install duckdb"

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path)) as connection:
        for name, frame in tables.items():
            local = frame.reset_index().rename(columns={frame.index.name or "index": "date"})
            connection.register("_incoming", local)
            connection.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _incoming')
            connection.unregister("_incoming")
    return str(database_path)
