import tkinter as tk
from collections.abc import Callable

from Experiment import SOURCE, SOURCE_PORT, Experiment, PortRef
from GUI import theme
from GUI.layout import SetupLayout, compute_layout
from Simulation import Beam, SimulationResult

COLUMN_WIDTH = 215
ROW_HEIGHT = 60
MARGIN = 26
NODE_WIDTH = 108
NODE_HEIGHT = 48
PORT_RADIUS = 8
PORT_SPACING = 22
MIN_BEAM_WIDTH = 1.5
MAX_EXTRA_BEAM_WIDTH = 8
BLOCK_POSITION = 0.25
EMPTY_BEAM_FRACTION = 1e-9


def _node_center(cell: tuple[int, float]) -> tuple[float, float]:
    column, row = cell
    return (
        MARGIN + NODE_WIDTH / 2 + column * COLUMN_WIDTH,
        MARGIN + NODE_HEIGHT / 2 + row * ROW_HEIGHT,
    )


def _flux_text(beam: Beam) -> str:
    if beam.count is not None:
        return f"{beam.count:,}"
    return f"{beam.probability:.1%}"


class SetupCanvas(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        on_node_click: Callable[[str | None], None],
        on_port_click: Callable[[PortRef, int, int], None],
    ) -> None:
        super().__init__(parent, background=theme.SURFACE, highlightthickness=0)
        self._on_node_click = on_node_click
        self._on_port_click = on_port_click
        self._click_actions: dict[int, Callable[[tk.Event], None]] = {}
        self.bind("<Button-1>", self._handle_click)
        self.tag_bind("clickable", "<Enter>", lambda _: self.configure(cursor="hand2"))
        self.tag_bind("clickable", "<Leave>", lambda _: self.configure(cursor=""))

    def render(
        self, experiment: Experiment, result: SimulationResult, selected: str | None
    ) -> None:
        self.delete("all")
        self._click_actions.clear()
        layout = compute_layout(experiment)
        anchors = self._port_anchors(experiment, layout)

        for port, start in anchors.items():
            self._draw_beam(experiment, result, layout, port, start)
        for node, cell in layout.nodes.items():
            self._draw_node(experiment, result, node, _node_center(cell), selected)
        for port, start in anchors.items():
            self._draw_port(port, start)

        _, _, right, bottom = self.bbox("all")
        self.configure(scrollregion=(0, 0, right + MARGIN, bottom + MARGIN))

    @staticmethod
    def _port_anchors(
        experiment: Experiment, layout: SetupLayout
    ) -> dict[PortRef, tuple[float, float]]:
        anchors = {}
        for node, cell in layout.nodes.items():
            center_x, center_y = _node_center(cell)
            ports = experiment.output_ports(node)
            for index, port_name in enumerate(ports):
                offset = (index - (len(ports) - 1) / 2) * PORT_SPACING
                anchors[PortRef(node, port_name)] = (
                    center_x + NODE_WIDTH / 2,
                    center_y + offset,
                )
        return anchors

    def _draw_beam(
        self,
        experiment: Experiment,
        result: SimulationResult,
        layout: SetupLayout,
        port: PortRef,
        start: tuple[float, float],
    ) -> None:
        target = experiment.target_of(port)
        cell = layout.exits[port] if target is None else layout.nodes[target]
        center_x, center_y = _node_center(cell)
        end = (center_x - NODE_WIDTH / 2, center_y)

        beam = result.beam_at(port)
        fraction = result.fraction_of(beam) if beam is not None else 0.0
        color = theme.port_color(port.port)

        if experiment.is_blocked(port):
            stop = (
                start[0] + (end[0] - start[0]) * BLOCK_POSITION,
                start[1] + (end[1] - start[1]) * BLOCK_POSITION,
            )
            self._draw_segment(start, stop, color, fraction)
            if target is not None:
                self._draw_segment(stop, end, color, 0.0)
            self._draw_beam_stop(beam, stop, rising=end[1] < start[1])
        else:
            arrow = tk.LAST if target is None else tk.NONE
            self._draw_segment(start, end, color, fraction, arrow)
            if beam is not None:
                self._draw_flux_label(beam, start, end, is_exit=target is None)

    def _draw_segment(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str,
        fraction: float,
        arrow: str = tk.NONE,
    ) -> None:
        if fraction > EMPTY_BEAM_FRACTION:
            width = MIN_BEAM_WIDTH + MAX_EXTRA_BEAM_WIDTH * fraction
            self.create_line(*start, *end, fill=color, width=width, arrow=arrow)
        else:
            self.create_line(
                *start, *end, fill=theme.BASELINE, width=1, dash=(3, 3), arrow=arrow
            )

    def _draw_beam_stop(
        self, beam: Beam | None, stop: tuple[float, float], rising: bool
    ) -> None:
        x, y = stop
        self.create_line(x, y - 11, x, y + 11, fill=theme.BLOCK_COLOR, width=4)
        text = "blocked" if beam is None else f"blocked {_flux_text(beam)}"
        self.create_text(
            x + 6,
            y + 3 if rising else y - 3,
            text=text,
            anchor="nw" if rising else "sw",
            fill=theme.BLOCK_COLOR,
            font=theme.FONT_SMALL,
        )

    def _draw_flux_label(
        self,
        beam: Beam,
        start: tuple[float, float],
        end: tuple[float, float],
        is_exit: bool,
    ) -> None:
        text = _flux_text(beam)
        if is_exit:
            self.create_text(
                end[0] + 6,
                end[1],
                text=text,
                anchor="w",
                fill=theme.INK,
                font=theme.FONT_BOLD,
            )
            return
        anchor = (
            "s" if abs(end[1] - start[1]) < 1 else "sw" if end[1] > start[1] else "se"
        )
        self.create_text(
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2 - 7,
            text=text,
            anchor=anchor,
            fill=theme.INK_SECONDARY,
            font=theme.FONT_SMALL,
        )

    def _draw_node(
        self,
        experiment: Experiment,
        result: SimulationResult,
        node: str,
        center: tuple[float, float],
        selected: str | None,
    ) -> None:
        x, y = center
        is_source = node == SOURCE
        label = experiment.source.label if is_source else experiment.device(node).label
        active = is_source or self._receives_particles(experiment, result, node)
        is_selected = node == selected

        outline = (
            theme.INK
            if is_selected
            else theme.INK_SECONDARY
            if active
            else theme.BASELINE
        )
        text_color = theme.INK if active else theme.INK_MUTED
        items = [
            self.create_rectangle(
                x - NODE_WIDTH / 2,
                y - NODE_HEIGHT / 2,
                x + NODE_WIDTH / 2,
                y + NODE_HEIGHT / 2,
                fill=theme.PANEL,
                outline=outline,
                width=2.5 if is_selected else 1,
                dash=() if active else (4, 3),
                tags="clickable",
            ),
            self.create_text(
                x,
                y - 10,
                text=node,
                fill=text_color,
                font=theme.FONT_BOLD,
                tags="clickable",
            ),
            self.create_text(
                x,
                y + 10,
                text=label,
                fill=text_color,
                font=theme.FONT_SMALL,
                tags="clickable",
            ),
        ]
        for item in items:
            self._click_actions[item] = lambda _event, name=node: self._on_node_click(
                name
            )

    @staticmethod
    def _receives_particles(
        experiment: Experiment, result: SimulationResult, node: str
    ) -> bool:
        incoming = experiment.input_of(node)
        beam = result.beam_at(incoming) if incoming is not None else None
        if beam is None or experiment.is_blocked(incoming):
            return False
        return result.fraction_of(beam) > EMPTY_BEAM_FRACTION

    def _draw_port(self, port: PortRef, center: tuple[float, float]) -> None:
        x, y = center
        items = [
            self.create_oval(
                x - PORT_RADIUS,
                y - PORT_RADIUS,
                x + PORT_RADIUS,
                y + PORT_RADIUS,
                fill=theme.port_color(port.port),
                outline=theme.SURFACE,
                width=2,
                tags="clickable",
            )
        ]
        if port != SOURCE_PORT:
            items.append(
                self.create_text(
                    x,
                    y,
                    text=port.port[:1],
                    fill="white",
                    font=theme.FONT_BOLD,
                    tags="clickable",
                )
            )
        for item in items:
            self._click_actions[item] = lambda event, ref=port: self._on_port_click(
                ref, event.x_root, event.y_root
            )

    def _handle_click(self, event: tk.Event) -> None:
        for item in self.find_withtag("current"):
            action = self._click_actions.get(item)
            if action is not None:
                action(event)
                return
        self._on_node_click(None)
