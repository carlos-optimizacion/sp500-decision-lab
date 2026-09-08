"""Configuración central y rutas reproducibles del proyecto."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path = PROJECT_ROOT

    @property
    def config(self) -> Path:
        return self.root / "config" / "settings.yaml"

    @property
    def raw(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def features(self) -> Path:
        return self.root / "data" / "features"

    @property
    def parquet(self) -> Path:
        return self.root / "database" / "parquet"

    @property
    def duckdb(self) -> Path:
        return self.root / "database" / "duckdb" / "decision_lab.duckdb"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def ensure(self) -> None:
        for path in (self.raw, self.processed, self.features, self.parquet, self.duckdb.parent, self.logs):
            path.mkdir(parents=True, exist_ok=True)


def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    """Carga YAML y resuelve la fecha final sin hardcodearla."""

    config_path = Path(path) if path else ProjectPaths().config
    with config_path.open("r", encoding="utf-8") as handle:
        settings: dict[str, Any] = yaml.safe_load(handle)
    settings["data"]["end_date"] = settings["data"].get("end_date") or date.today().isoformat()
    return settings


def deep_get(mapping: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    current: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current

