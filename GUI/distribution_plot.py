from tkinter import ttk
from typing import NamedTuple

import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import (
    FuncFormatter,
    MaxNLocator,
    MultipleLocator,
    PercentFormatter,
)

from GUI import theme
from Simulation import SimulationResult

matplotlib.rcParams["font.sans-serif"] = [theme.FONT_FAMILY, "DejaVu Sans"]

MAX_BAR_PIXELS = 24
TOP_HEADROOM = 1.14
MAX_HORIZONTAL_LABELS = 8


class _Bar(NamedTuple):
    label: str
    height: float
    expected: float
    color: str


def describe_spin(spin: tuple[float, float, float] | None) -> str:
    if spin is None:
        return "no particles"
    bloch = np.array(spin)
    if np.linalg.norm(bloch) < 1e-9:
        return "unpolarized"
    for name, axis in zip("xyz", np.eye(3)):
        if np.allclose(bloch, axis, atol=1e-9):
            return f"spin +{name}"
        if np.allclose(bloch, -axis, atol=1e-9):
            return f"spin −{name}"
    return f"r = ({bloch[0]:.2f}, {bloch[1]:.2f}, {bloch[2]:.2f})"


def _collect_bars(result: SimulationResult) -> list[_Bar]:
    scale = result.total_particles if result.is_sampled else 1

    def height(beam) -> float:
        return beam.count if result.is_sampled else beam.probability

    bars = [
        _Bar(
            f"{beam.label}\n{describe_spin(beam.spin)}",
            height(beam),
            beam.probability * scale,
            theme.port_color(beam.port.port),
        )
        for beam in result.exits
    ]
    if result.blocked:
        bars.append(
            _Bar(
                "Blocked",
                sum(height(beam) for beam in result.blocked),
                sum(beam.probability for beam in result.blocked) * scale,
                theme.BLOCKED_BAR_COLOR,
            )
        )
    return bars


class DistributionPlot(ttk.Frame):
    def __init__(self, parent: ttk.Widget) -> None:
        super().__init__(parent)
        self._figure = Figure(
            figsize=(7, 3), facecolor=theme.SURFACE, layout="constrained"
        )
        self._axes = self._figure.add_subplot()
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._result: SimulationResult | None = None
        self._canvas.mpl_connect("resize_event", lambda _: self._draw_latest())

    def render(self, result: SimulationResult) -> None:
        self._result = result
        self._draw_latest()

    def _draw_latest(self) -> None:
        if self._result is None:
            return
        axes = self._axes
        axes.clear()
        bars = _collect_bars(self._result)
        self._style_axes()
        if bars:
            self._draw_bars(bars)
            self._draw_legend(bars)
        self._canvas.draw_idle()

    def _style_axes(self) -> None:
        axes, result = self._axes, self._result
        mode = (
            f"{result.total_particles:,} simulated particles"
            if result.is_sampled
            else "exact probabilities"
        )
        axes.set_title(
            f"Final spin distribution: {mode}",
            loc="left",
            fontsize=10,
            fontweight="bold",
            color=theme.INK,
        )
        if result.is_sampled:
            axes.set_ylabel("Particles", fontsize=9, color=theme.INK_SECONDARY)
            axes.set_ylim(0, result.total_particles * TOP_HEADROOM)
            axes.yaxis.set_major_locator(MaxNLocator(5, integer=True))
            axes.yaxis.set_major_formatter(
                FuncFormatter(lambda value, _: f"{value:,.0f}")
            )
        else:
            axes.set_ylabel("Probability", fontsize=9, color=theme.INK_SECONDARY)
            axes.set_ylim(0, TOP_HEADROOM)
            axes.yaxis.set_major_locator(MultipleLocator(0.25))
            axes.yaxis.set_major_formatter(PercentFormatter(1.0))

        axes.set_facecolor(theme.SURFACE)
        axes.set_axisbelow(True)
        axes.grid(axis="y", color=theme.GRIDLINE, linewidth=0.8)
        axes.spines[["top", "right", "left"]].set_visible(False)
        axes.spines["bottom"].set_color(theme.BASELINE)
        axes.tick_params(axis="y", length=0, labelsize=8, labelcolor=theme.INK_MUTED)
        axes.tick_params(
            axis="x", length=0, labelsize=8, labelcolor=theme.INK_SECONDARY
        )

    def _draw_bars(self, bars: list[_Bar]) -> None:
        axes, result = self._axes, self._result
        positions = np.arange(len(bars))
        axes.set_xlim(-0.5, len(bars) - 0.5)
        pixels_per_bar = axes.get_window_extent().width / len(bars)
        width = min(0.7, MAX_BAR_PIXELS / pixels_per_bar)

        axes.bar(
            positions,
            [bar.height for bar in bars],
            width,
            color=[bar.color for bar in bars],
        )
        if result.is_sampled:
            axes.hlines(
                [bar.expected for bar in bars],
                positions - width * 0.85,
                positions + width * 0.85,
                color=theme.INK,
                linewidth=2,
            )

        value_format = "{:,}" if result.is_sampled else "{:.1%}"
        for position, bar in zip(positions, bars):
            axes.annotate(
                value_format.format(bar.height),
                (position, max(bar.height, bar.expected)),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=theme.INK,
            )

        axes.set_xticks(positions, [bar.label for bar in bars])
        if len(bars) > MAX_HORIZONTAL_LABELS:
            axes.tick_params(axis="x", labelrotation=30)

    def _draw_legend(self, bars: list[_Bar]) -> None:
        colors = {bar.color for bar in bars}
        handles = [
            Patch(color=color, label=f"{port} beam")
            for port, color in theme.PORT_COLORS.items()
            if color in colors
        ]
        if theme.BLOCKED_BAR_COLOR in colors:
            handles.append(Patch(color=theme.BLOCKED_BAR_COLOR, label="Blocked"))
        if self._result.is_sampled:
            handles.append(
                Line2D(
                    [], [], color=theme.INK, linewidth=2, label="Exact expected value"
                )
            )
        if handles:
            self._axes.legend(
                handles=handles,
                loc="lower right",
                bbox_to_anchor=(1, 1),
                ncols=len(handles),
                frameon=False,
                fontsize=8,
                labelcolor=theme.INK_SECONDARY,
                borderaxespad=0,
            )
