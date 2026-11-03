import tkinter as tk
from collections.abc import Callable
from math import degrees, radians
from tkinter import ttk

from Experiment import (
    NAMED_AXES,
    SOURCE,
    Experiment,
    Source,
    SternGerlachDevice,
)
from GUI import theme


class _Slider(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        maximum: int,
        unit: str,
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._unit = unit
        self._on_change = on_change
        self.value = 0
        self._position = tk.DoubleVar(self, 0.0)
        self._readout = tk.StringVar(self, f"0{unit}")
        ttk.Label(self, text=title, font=theme.FONT_BODY).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(self, textvariable=self._readout, font=theme.FONT_BODY).grid(
            row=0, column=1, sticky="e"
        )
        ttk.Scale(
            self, from_=0, to=maximum, variable=self._position, command=self._on_drag
        ).grid(row=1, column=0, columnspan=2, sticky="ew")
        self.columnconfigure(0, weight=1)

    def _on_drag(self, raw_position: str) -> None:
        value = round(float(raw_position))
        if value != self.value:
            self.show(value)
            self._on_change()

    def show(self, value: float) -> None:
        self.value = round(value)
        self._position.set(self.value)
        self._readout.set(f"{self.value}{self._unit}")


class OrientationControls(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_change: Callable[[], None]) -> None:
        super().__init__(parent)
        self._on_change = on_change
        self._theta = _Slider(self, "θ (angle from z)", 180, "°", on_change)
        self._phi = _Slider(self, "φ (angle around z)", 360, "°", on_change)

        buttons = ttk.Frame(self)
        ttk.Label(buttons, text="Axis", font=theme.FONT_BODY).pack(
            side="left", padx=(0, 8)
        )
        for name in NAMED_AXES:
            ttk.Button(
                buttons,
                text=name,
                width=3,
                command=lambda axis=name: self._use_axis(axis),
            ).pack(side="left", padx=(0, 4))

        buttons.pack(fill="x", pady=(0, 8))
        self._theta.pack(fill="x", pady=(0, 8))
        self._phi.pack(fill="x")

    @property
    def angles(self) -> tuple[float, float]:
        return radians(self._theta.value), radians(self._phi.value)

    def show(self, theta: float, phi: float) -> None:
        self._theta.show(degrees(theta))
        self._phi.show(degrees(phi))

    def _use_axis(self, name: str) -> None:
        self.show(*NAMED_AXES[name])
        self._on_change()


class SternGerlachEditor(ttk.Frame):
    def __init__(
        self, parent: tk.Misc, on_change: Callable[[SternGerlachDevice], None]
    ) -> None:
        super().__init__(parent)
        self._orientation = OrientationControls(
            self, lambda: on_change(SternGerlachDevice(*self._orientation.angles))
        )
        self._orientation.pack(fill="x")

    def sync(self, device: SternGerlachDevice) -> None:
        self._orientation.show(device.theta, device.phi)


class SourceEditor(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_change: Callable[[Source], None]) -> None:
        super().__init__(parent)
        self._on_change = on_change
        self._polarization = _Slider(self, "Polarization", 100, "%", self._report)
        self._orientation = OrientationControls(self, self._report)
        self._polarization.pack(fill="x", pady=(0, 2))
        ttk.Label(
            self,
            text="0% is an unpolarized oven; 100% is a pure spin state. "
            "The direction has no effect at 0%.",
            wraplength=220,
            font=theme.FONT_SMALL,
            foreground=theme.INK_SECONDARY,
        ).pack(fill="x", pady=(0, 10))
        self._orientation.pack(fill="x")

    def _report(self) -> None:
        self._on_change(
            Source(self._polarization.value / 100, *self._orientation.angles)
        )

    def sync(self, source: Source) -> None:
        self._polarization.show(source.polarization * 100)
        self._orientation.show(source.theta, source.phi)


DEVICE_EDITORS = {SternGerlachDevice: SternGerlachEditor}


class Inspector(ttk.LabelFrame):
    def __init__(
        self, parent: tk.Misc, on_remove_device: Callable[[str], None]
    ) -> None:
        super().__init__(parent, text="Selection", padding=10)
        self._on_remove_device = on_remove_device
        self._experiment: Experiment | None = None
        self._node: str | None = None
        self._editor: SourceEditor | SternGerlachEditor | None = None

    def show(self, experiment: Experiment, node: str | None) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._experiment, self._node, self._editor = experiment, node, None

        if node is None:
            self.configure(text="Selection")
            ttk.Label(
                self,
                text="Click the source or a device in the diagram to edit it.",
                wraplength=220,
                font=theme.FONT_BODY,
                foreground=theme.INK_SECONDARY,
            ).pack(fill="x")
            return

        if node == SOURCE:
            self.configure(text="Source")
            self._editor = SourceEditor(self, experiment.set_source)
        else:
            self.configure(text=f"Device {node}")
            editor_class = DEVICE_EDITORS.get(type(experiment.device(node)))
            if editor_class is not None:
                self._editor = editor_class(
                    self, lambda device: experiment.replace_device(node, device)
                )
        if self._editor is not None:
            self._editor.pack(fill="x")
        if node != SOURCE:
            ttk.Button(
                self, text="Remove device", command=lambda: self._on_remove_device(node)
            ).pack(fill="x", pady=(14, 0))
        self.sync()

    def sync(self) -> None:
        if self._editor is None:
            return
        if self._node == SOURCE:
            self._editor.sync(self._experiment.source)
        else:
            self._editor.sync(self._experiment.device(self._node))
