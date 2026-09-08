"""Sistema visual sobrio y consistente para todas las figuras."""

INK = "#172033"
MUTED = "#667085"
GRID = "#E6EAF0"
BLUE = "#1F5EFF"
BLUE_LIGHT = "#AFC6FF"
GOLD = "#D6A84B"
ORANGE = "#E57A44"
PINK = "#C65C8A"
OLIVE = "#7C8A4B"
WHITE = "#FFFFFF"
PALE = "#F6F7FB"

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
        "paper_bgcolor": WHITE,
        "plot_bgcolor": WHITE,
        "font": {"family": "Inter, Arial, sans-serif", "color": INK, "size": 12},
        "margin": {"l": 54, "r": 28, "t": 76, "b": 48},
        "hovermode": "x unified",
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    }


def axis(title: str = "", percent: bool = False) -> dict:
    output = {
        "title": title,
        "showgrid": True,
        "gridcolor": GRID,
        "zeroline": False,
        "showline": True,
        "linecolor": "#CBD1DB",
        "fixedrange": False,
    }
    if percent:
        output["tickformat"] = ".0%"
    return output

