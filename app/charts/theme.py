"""Sistema visual oscuro y consistente para todas las figuras."""

INK = "#E5E7EB"
MUTED = "#94A3B8"
GRID = "#293548"
AXIS = "#475569"
BLUE = "#5B8CFF"
BLUE_LIGHT = "#91B4FF"
GOLD = "#E6B85C"
ORANGE = "#FF8A5B"
PINK = "#E879B0"
OLIVE = "#A3B86C"
PANEL = "#111827"

REGIME_COLORS = {
    "Bull": BLUE,
    "Neutral": "#98A2B3",
    "Correction": GOLD,
    "Stress": ORANGE,
}


def layout(title: str, subtitle: str = "", height: int = 420) -> dict:
    title_text = f"<b>{title}</b>"
    if subtitle:
        title_text += f"<br><sup>{subtitle}</sup>"
    return {
        "title": {"text": title_text, "x": 0.01, "xanchor": "left", "font": {"size": 16, "color": INK}},
        "height": height,
        "paper_bgcolor": PANEL,
        "plot_bgcolor": PANEL,
        "font": {"family": "Inter, Arial, sans-serif", "color": INK, "size": 12},
        "margin": {"l": 54, "r": 28, "t": 76, "b": 48},
        "hovermode": "x unified",
        "dragmode": False,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    }


def axis(title: str = "", percent: bool = False) -> dict:
    output = {
        "title": title,
        "showgrid": True,
        "gridcolor": GRID,
        "zeroline": False,
        "showline": True,
        "linecolor": AXIS,
        "fixedrange": True,
    }
    if percent:
        output["tickformat"] = ".0%"
    return output
