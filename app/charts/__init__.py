"""Gráficos Plotly del dashboard."""

INTERACTIVE_PLOT_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

STATIC_PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}

__all__ = ["INTERACTIVE_PLOT_CONFIG", "STATIC_PLOT_CONFIG"]
