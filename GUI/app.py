import tkinter as tk
from tkinter import ttk

from Experiment import DEVICE_CATALOG, SOURCE, Device, PortRef
from Experiment.presets import DEFAULT_PRESET, PRESETS
from GUI import theme
from GUI.distribution_plot import DistributionPlot
from GUI.inspector import Inspector
from GUI.setup_canvas import SetupCanvas
from Simulation import ExactEngine, LiveSimulation, MonteCarloEngine

MODE_EXACT = "exact"
MODE_PARTICLES = "particles"
DEFAULT_PARTICLES = 10_000
MAX_PARTICLES = 100_000_000

HELP_TEXT = (
    "Click a device or the source to edit it.  "
    "Click a colored port to block it, add a device or make a connection."
)


class SternGerlachApp(ttk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self._live = LiveSimulation(PRESETS[DEFAULT_PRESET](), ExactEngine())
        self._selected: str | None = None
        self._refresh_scheduled = False
        self._last_valid_particles = DEFAULT_PARTICLES

        self._build_toolbar()
        self._build_body()

        self._live.subscribe(self._schedule_refresh)
        self._inspector.show(self._live.experiment, None)
        self._refresh()

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="Configuration").pack(side="left", padx=(0, 6))
        self._preset = tk.StringVar(self, DEFAULT_PRESET)
        presets = ttk.Combobox(
            toolbar,
            textvariable=self._preset,
            values=list(PRESETS),
            state="readonly",
            width=30,
        )
        presets.pack(side="left", padx=(0, 22))
        presets.bind("<<ComboboxSelected>>", lambda _: self._load_preset())

        ttk.Label(toolbar, text="Simulation mode").pack(side="left", padx=(0, 6))
        self._mode = tk.StringVar(self, MODE_EXACT)
        for text, mode in (("Percent", MODE_EXACT), ("Particles", MODE_PARTICLES)):
            ttk.Radiobutton(
                toolbar,
                text=text,
                value=mode,
                variable=self._mode,
                command=self._apply_mode,
            ).pack(side="left", padx=(0, 8))

        self._particles = tk.StringVar(self, str(DEFAULT_PARTICLES))
        self._particles_box = ttk.Spinbox(
            toolbar,
            textvariable=self._particles,
            from_=100,
            to=MAX_PARTICLES,
            increment=1000,
            width=11,
            command=self._apply_mode,
            state="disabled",
        )
        self._particles_box.pack(side="left")
        self._particles_box.bind("<Return>", lambda _: self._apply_mode())
        self._particles_box.bind("<FocusOut>", lambda _: self._apply_mode())

    def _build_body(self) -> None:
        body = ttk.Frame(self, padding=(10, 0, 10, 0))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=5)
        body.rowconfigure(1, weight=4)

        diagram = ttk.Frame(body)
        diagram.grid(row=0, column=0, sticky="nsew")
        diagram.columnconfigure(0, weight=1)
        diagram.rowconfigure(0, weight=1)
        self._canvas = SetupCanvas(diagram, self._select, self._show_port_menu)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(diagram, orient="vertical", command=self._canvas.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(
            diagram, orient="horizontal", command=self._canvas.xview
        )
        horizontal.grid(row=1, column=0, sticky="ew")
        self._canvas.configure(
            xscrollcommand=horizontal.set, yscrollcommand=vertical.set
        )

        self._plot = DistributionPlot(body)
        self._plot.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        self._inspector = Inspector(body, self._remove_device)
        self._inspector.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        self._inspector.configure(width=250)
        self._inspector.pack_propagate(False)

        ttk.Label(
            self,
            text=HELP_TEXT,
            padding=(10, 6),
            font=theme.FONT_BODY,
            foreground=theme.INK_SECONDARY,
        ).pack(fill="x")

    def _schedule_refresh(self) -> None:
        if not self._refresh_scheduled:
            self._refresh_scheduled = True
            self.after_idle(self._refresh)

    def _refresh(self) -> None:
        self._refresh_scheduled = False
        experiment = self._live.experiment
        if self._selected not in (None, SOURCE, *experiment.device_names):
            self._selected = None
            self._inspector.show(experiment, None)
        self._canvas.render(experiment, self._live.result, self._selected)
        self._plot.render(self._live.result)
        self._inspector.sync()

    def _select(self, node: str | None) -> None:
        self._selected = node
        self._inspector.show(self._live.experiment, node)
        self._schedule_refresh()

    def _load_preset(self) -> None:
        self._live.load_experiment(PRESETS[self._preset.get()]())
        self._select(None)

    def _apply_mode(self) -> None:
        if self._mode.get() == MODE_EXACT:
            self._particles_box.configure(state="disabled")
            engine = ExactEngine()
        else:
            self._particles_box.configure(state="normal")
            engine = MonteCarloEngine(self._read_particle_count())
        self._live.set_engine(engine)

    def _read_particle_count(self) -> int:
        try:
            value = int(self._particles.get().replace(",", ""))
            if not 1 <= value <= MAX_PARTICLES:
                raise ValueError
        except ValueError:
            self._particles.set(str(self._last_valid_particles))
            return self._last_valid_particles
        self._last_valid_particles = value
        return value

    def _remove_device(self, name: str) -> None:
        self._live.experiment.remove_device(name)

    def _show_port_menu(self, port: PortRef, x: int, y: int) -> None:
        experiment = self._live.experiment
        menu = tk.Menu(self, tearoff=False)

        blocked = experiment.is_blocked(port)
        menu.add_command(
            label="Unblock this path" if blocked else "Block this path",
            command=lambda: experiment.set_blocked(port, not blocked),
        )
        menu.add_separator()

        current_target = experiment.target_of(port)
        if current_target is not None:
            menu.add_command(
                label=f"Disconnect from {current_target}",
                command=lambda: experiment.disconnect(port),
            )
        else:
            for title, factory in DEVICE_CATALOG.items():
                menu.add_command(
                    label=f"Add {title} device here",
                    command=lambda create=factory: self._attach_new_device(
                        port, create()
                    ),
                )
            for name in experiment.connectable_targets(port):
                menu.add_command(
                    label=f"Connect to {name}",
                    command=lambda target=name: experiment.connect(port, target),
                )
        menu.tk_popup(x, y)

    def _attach_new_device(self, port: PortRef, device: Device) -> None:
        experiment = self._live.experiment
        name = experiment.add_device(device)
        experiment.connect(port, name)
        self._select(name)


def run_app() -> None:
    root = tk.Tk()
    root.title("Stern-Gerlach Simulation")
    root.geometry("1280x820")
    root.minsize(900, 600)
    SternGerlachApp(root).pack(fill="both", expand=True)
    root.mainloop()
