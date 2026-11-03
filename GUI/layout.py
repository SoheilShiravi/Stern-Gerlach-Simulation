from dataclasses import dataclass

from Experiment import SOURCE, Experiment, PortRef

GridPoint = tuple[int, float]


@dataclass(frozen=True)
class SetupLayout:
    nodes: dict[str, GridPoint]
    exits: dict[PortRef, GridPoint]


def compute_layout(experiment: Experiment) -> SetupLayout:
    nodes: dict[str, GridPoint] = {}
    exits: dict[PortRef, GridPoint] = {}
    next_free_row = 0

    def place(node: str, column: int) -> float:
        nonlocal next_free_row
        child_rows = []
        for port_name in experiment.output_ports(node):
            port = PortRef(node, port_name)
            target = experiment.target_of(port)
            if target is None:
                exits[port] = (column + 1, float(next_free_row))
                child_rows.append(float(next_free_row))
                next_free_row += 1
            else:
                child_rows.append(place(target, column + 1))
        row = sum(child_rows) / len(child_rows)
        nodes[node] = (column, row)
        return row

    place(SOURCE, 0)
    for name in experiment.device_names:
        if experiment.input_of(name) is None:
            place(name, 1)
    return SetupLayout(nodes, exits)
