SURFACE = "#fcfcfb"
PANEL = "#f9f9f7"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

PORT_COLORS = {"+": "#2a78d6", "-": "#eb6834"}
OTHER_PORT_COLOR = "#52514e"

BLOCK_COLOR = "#d03b3b"
BLOCKED_BAR_COLOR = "#898781"

FONT_FAMILY = "Segoe UI"
FONT_BODY = (FONT_FAMILY, 9)
FONT_SMALL = (FONT_FAMILY, 8)
FONT_BOLD = (FONT_FAMILY, 10, "bold")


def port_color(port_name: str) -> str:
    return PORT_COLORS.get(port_name, OTHER_PORT_COLOR)
