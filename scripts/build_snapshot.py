"""Genera el dataset real y todos los resultados consumidos por Streamlit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.analysis import build_analysis
from core.config import ProjectPaths
from core.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Descarga nuevamente todas las fuentes")
    args = parser.parse_args()
    paths = ProjectPaths()
    configure_logging(paths.logs / "snapshot.log")
    bundle = build_analysis(refresh=args.refresh)
    current = bundle.decisions.iloc[-1]
    print(
        f"Snapshot {bundle.experiment['experiment_id']} | {current.name.date()} | "
        f"OS={current['opportunity_score']:.1f} RS={current['risk_score']:.1f} "
        f"CS={current['confidence_score']:.1f} | {current['decision_state']}"
    )


if __name__ == "__main__":
    main()
