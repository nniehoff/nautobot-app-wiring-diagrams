"""Build a wiring graph for a Location, Rack, or Device from Nautobot cables."""

from collections import defaultdict
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from nautobot.dcim.constants import TERMINATION_FK_TO_PARENT_FK
from nautobot.dcim.models import Cable, CablePath, Device, Location, Rack

# Termination FKs on CableToCableTermination, grouped into user-selectable connection kinds.
CONNECTION_KINDS = {
    "data": ("interface", "front_port", "rear_port", "circuit_termination"),
    "console": ("console_port", "console_server_port"),
    "power": ("power_port", "power_outlet", "power_feed"),
}
# Power is left out by default: UPS and PDU cables cross the whole diagram.
DEFAULT_KINDS = ("data", "console")
KIND_OF_FK = {fk: kind for kind, fks in CONNECTION_KINDS.items() for fk in fks}
# Patch panel ports; hidden when patch panels are collapsed.
PASS_THROUGH_FKS = ("front_port", "rear_port")
# Display order of port kinds within a node.
PORT_KIND_ORDER = {
    fk: index
    for index, fk in enumerate(
        (
            "interface",
            "front_port",
            "rear_port",
            "circuit_termination",
            "console_port",
            "console_server_port",
            "power_port",
            "power_outlet",
            "power_feed",
        )
    )
}


@dataclass
class DiagramOptions:
    """What to include in a wiring graph."""

    cable_types: list = field(default_factory=list)
    statuses: list = field(default_factory=list)
    kinds: list = field(default_factory=lambda: list(DEFAULT_KINDS))
    collapse_patch_panels: bool = False

    @property
    def termination_fks(self):
        """Termination FK names selected by `kinds`."""
        return [fk for kind in self.kinds for fk in CONNECTION_KINDS[kind]]


@dataclass
class Port:
    """One cabled port on a node."""

    id: str
    name: str
    url: str
    sort_key: tuple


@dataclass
class Node:  # pylint: disable=too-many-instance-attributes
    """A device, circuit, or power panel in the diagram."""

    id: str
    label: str
    subtitle: str
    url: str
    in_scope: bool
    group: str = ""
    rack: str = ""
    position: int = None
    ports: dict = field(default_factory=dict)

    def sorted_ports(self):
        """Ports in display order."""
        return sorted(self.ports.values(), key=lambda port: port.sort_key)


@dataclass
class Edge:
    """A cable (or, when collapsed, an end-to-end path) between two ports."""

    a_node: str
    a_port: str
    b_node: str
    b_port: str
    cable: Cable
    via_patch_panel: bool = False
    kind: str = "data"


class WiringGraph:
    """Nodes and edges of a wiring diagram."""

    def __init__(self, device_ids=()):
        """Create an empty graph; `device_ids` are the devices in scope."""
        self.device_ids = set(device_ids)
        self.nodes = {}
        self.edges = []

    def endpoint(self, termination):
        """Return `(node, port)` for a cable termination, adding them if needed, or None if it has no parent."""
        parent = termination.parent
        if parent is None:
            return None
        node_key = _object_key(parent)
        node = self.nodes.get(node_key)
        if node is None:
            node = self._make_node(parent)
            self.nodes[node_key] = node
        port_key = _object_key(termination)
        port = node.ports.get(port_key)
        if port is None:
            port = Port(
                id=f"p{len(node.ports)}",
                name=port_name(termination),
                url=termination.get_absolute_url(),
                sort_key=(
                    PORT_KIND_ORDER.get(termination_fk(termination), 99),
                    getattr(termination, "_name", "") or str(termination),
                ),
            )
            node.ports[port_key] = port
        return node, port

    def add_edge(self, a_termination, b_termination, cable, via_patch_panel=False):
        """Add an edge between two terminations."""
        a_end = self.endpoint(a_termination)
        b_end = self.endpoint(b_termination)
        if a_end is None or b_end is None:
            return
        self.edges.append(
            Edge(
                a_node=a_end[0].id,
                a_port=a_end[1].id,
                b_node=b_end[0].id,
                b_port=b_end[1].id,
                cable=cable,
                via_patch_panel=via_patch_panel,
                kind=KIND_OF_FK.get(termination_fk(a_termination), "data"),
            )
        )

    def _make_node(self, parent):
        node_id = f"n{len(self.nodes)}"
        if isinstance(parent, Device):
            return Node(
                id=node_id,
                label=parent.name or str(parent),
                subtitle=str(parent.device_type.model) if parent.device_type_id else "",
                url=parent.get_absolute_url(),
                in_scope=parent.pk in self.device_ids,
                group=parent.rack.name if parent.rack_id and parent.pk in self.device_ids else "",
                rack=parent.rack.name if parent.rack_id else "",
                position=parent.position,
            )
        return Node(
            id=node_id,
            label=str(parent),
            subtitle=parent._meta.verbose_name.title(),
            url=parent.get_absolute_url(),
            in_scope=False,
        )


def termination_fk(termination):
    """Return the CableToCableTermination FK name for a termination instance."""
    model_name = termination._meta.model_name
    for fk in TERMINATION_FK_TO_PARENT_FK:
        if fk.replace("_", "") == model_name:
            return fk
    return ""


def port_name(termination):
    """Short display name for a termination."""
    if termination._meta.model_name == "circuittermination":
        return f"Term {termination.term_side}"
    return termination.name


def scope_devices(scope_obj):
    """Return the Device queryset covered by a Location, Rack, or Device."""
    if isinstance(scope_obj, Device):
        return Device.objects.filter(pk=scope_obj.pk)
    if isinstance(scope_obj, Rack):
        return Device.objects.filter(rack=scope_obj)
    if isinstance(scope_obj, Location):
        # Materialize the pks; the tree CTE can't be nested as an `__in` subquery.
        location_pks = list(scope_obj.descendants(include_self=True).values_list("pk", flat=True))
        return Device.objects.filter(location__in=location_pks)
    raise TypeError(f"Unsupported wiring diagram scope: {type(scope_obj).__name__}")


def build_graph(scope_obj, options=None, user=None):
    """Build a WiringGraph of the cables attached to devices in `scope_obj`."""
    options = options or DiagramOptions()
    devices = scope_devices(scope_obj)
    if user is not None:
        devices = devices.restrict(user, "view")
    graph = WiringGraph(devices.values_list("pk", flat=True))

    fks = options.termination_fks
    cables = _cable_queryset(graph.device_ids, options, user)
    if cables is None:
        return graph

    path_origins = {}
    for cable in cables:
        rows = [row for row in cable.terminations.all() if termination_fk_of_row(row) in fks]
        if options.collapse_patch_panels and any(termination_fk_of_row(row) in PASS_THROUGH_FKS for row in rows):
            for row in rows:
                if termination_fk_of_row(row) not in PASS_THROUGH_FKS:
                    path_origins[row.termination] = cable
            continue
        a_side = [row.termination for row in rows if row.cable_end == "A"]
        b_side = [row.termination for row in rows if row.cable_end == "B"]
        for a_term in a_side:
            for b_term in b_side:
                graph.add_edge(a_term, b_term, cable)

    if path_origins:
        _add_path_edges(graph, path_origins)
    return graph


def _cable_queryset(device_ids, options, user):
    """Cables with a selected-kind termination on a device in `device_ids`, or None if nothing can match."""
    fks = options.termination_fks
    device_fks = [fk for fk in fks if TERMINATION_FK_TO_PARENT_FK[fk] == "device"]
    if not device_ids or not device_fks:
        return None

    in_scope = Q()
    for fk in device_fks:
        in_scope |= Q(**{f"terminations__{fk}__device__in": device_ids})
    cables = Cable.objects.filter(in_scope)
    if user is not None:
        cables = cables.restrict(user, "view")
    if options.cable_types:
        cables = cables.filter(type__in=options.cable_types)
    if options.statuses:
        cables = cables.filter(status__in=options.statuses)
    prefetch = []
    for fk in fks:
        parent = TERMINATION_FK_TO_PARENT_FK[fk]
        prefetch.append(f"terminations__{fk}__{parent}")
        if parent == "device":
            prefetch += [f"terminations__{fk}__{parent}__rack", f"terminations__{fk}__{parent}__device_type"]
    return cables.distinct().select_related("status").prefetch_related(*prefetch)


def termination_fk_of_row(row):
    """Return the FK name that is set on a CableToCableTermination row."""
    for fk in TERMINATION_FK_TO_PARENT_FK:
        if getattr(row, f"{fk}_id", None) is not None:
            return fk
    return ""


def _add_path_edges(graph, path_origins):
    """Add end-to-end edges through patch panels for endpoints whose cable lands on a panel."""
    by_model = {}
    for termination in path_origins:
        by_model.setdefault(type(termination), []).append(termination)
    seen = set()
    for model, terminations in by_model.items():
        lookup = {termination.pk: termination for termination in terminations}
        paths = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(model), origin_id__in=list(lookup)
        ).prefetch_related("destination")
        resolved = set()
        for path in paths:
            if path.destination is None or path.is_split:
                continue
            origin = lookup[path.origin_id]
            resolved.add(origin.pk)
            key = frozenset((_object_key(origin), _object_key(path.destination)))
            if key not in seen:
                seen.add(key)
                graph.add_edge(origin, path.destination, path_origins[origin], via_patch_panel=True)
        # Paths that end at an unconnected panel port: draw the cable to the panel instead.
        for origin in terminations:
            peer = None if origin.pk in resolved else origin.get_cable_peer()
            if peer is not None:
                graph.add_edge(origin, peer, path_origins[origin])


def _object_key(obj):
    """Key unique across models."""
    return f"{obj._meta.label_lower}:{obj.pk}"


def assign_columns(graph):
    """Place each node in a column: busiest devices at 0, their peers at -1/+1, the peers' peers at -2/+2, ...

    Within each connected group of nodes, those with at least two thirds as many cabled ports as the busiest one
    form the middle column. Every other node goes one column further out than the neighbor that reaches it first, on
    the same side, so most cables span a single column. A redundant pair (two busiest nodes) is split instead;
    see `_pair_columns`.
    """
    neighbors = _neighbors(graph)
    ports = {node.id: len(node.ports) for node in graph.nodes.values()}
    labels = {node.id: node.label for node in graph.nodes.values()}
    columns = {}
    side_sizes = {-1: 0, 1: 0}
    for component in _components(ports, neighbors):
        busiest = max(ports[node_id] for node_id in component)
        core = sorted(
            (node_id for node_id in component if ports[node_id] * 3 >= busiest * 2),
            key=lambda node_id: (labels[node_id], node_id),
        )
        if busiest <= 1:
            core = core[:1]  # Only single cables: one end in the middle, the other beside it.
        branches = _branches(core, neighbors, ports)
        if len(core) == 2:
            columns.update(_pair_columns(core, branches, neighbors))
        else:
            columns.update(dict.fromkeys(core, 0))
            _side_columns(branches, neighbors, columns, side_sizes)
    return columns


def _neighbors(graph):
    """Map node id to the ids of the nodes it is cabled to."""
    neighbors = defaultdict(set)
    for edge in graph.edges:
        if edge.a_node != edge.b_node:
            neighbors[edge.a_node].add(edge.b_node)
            neighbors[edge.b_node].add(edge.a_node)
    return neighbors


def _side_columns(branches, neighbors, columns, side_sizes):
    """Send each branch left or right of the middle: toward more of its neighbors, else to the emptier side."""
    for root, members in sorted(branches.items(), key=lambda item: (-len(item[1]), item[0])):
        placed = [columns[peer] for peer in neighbors[root] if peer in columns]
        affinity = {-1: sum(column < 0 for column in placed), 1: sum(column > 0 for column in placed)}
        side = max((-1, 1), key=lambda candidate, affinity=affinity: (affinity[candidate], -side_sizes[candidate]))
        side_sizes[side] += len(members)
        for node_id, depth in members:
            columns[node_id] = side * depth


def _pair_columns(core, branches, neighbors):
    """Columns for a redundant pair: `left | nodes cabled to both | right`.

    Nodes cabled to both members sit in column 0, so each has one short cable to either side. Whatever hangs
    off them fills the columns between them and the pair, and nodes cabled to one member go outside it.
    """
    left, right = core
    shared = {root for root in branches if {left, right} <= neighbors[root]}
    reach = max((depth for root in shared for _, depth in branches[root]), default=1)
    columns = {left: -reach, right: reach}
    side_sizes = {-1: 0, 1: 0}
    for root, members in sorted(branches.items(), key=lambda item: (-len(item[1]), item[0])):
        if root in shared:
            side = min((-1, 1), key=lambda candidate: (side_sizes[candidate], candidate))
            side_sizes[side] += len(members) - 1
            for node_id, depth in members:
                columns[node_id] = side * (depth - 1)
        else:
            side = -1 if left in neighbors[root] else 1
            for node_id, depth in members:
                columns[node_id] = side * (reach + depth)
    return columns


def _components(node_ids, neighbors):
    """Connected groups of node ids, largest first."""
    seen = set()
    components = []
    for start in node_ids:
        if start in seen:
            continue
        seen.add(start)
        component, queue = [], [start]
        while queue:
            node_id = queue.pop()
            component.append(node_id)
            for peer in sorted(neighbors[node_id] - seen):
                seen.add(peer)
                queue.append(peer)
        components.append(sorted(component))
    return sorted(components, key=len, reverse=True)


def _branches(core, neighbors, ports):
    """Breadth-first from `core`: map each first-ring node to `[(node_id, depth), ...]` reached through it."""
    depth = dict.fromkeys(core, 0)
    root_of = {}
    ring = list(core)
    while ring:
        next_ring = []
        for node_id in sorted(ring, key=lambda node_id: (-ports[node_id], node_id)):
            for peer in sorted(neighbors[node_id]):
                if peer in depth:
                    continue
                depth[peer] = depth[node_id] + 1
                root_of[peer] = root_of.get(node_id, peer)
                next_ring.append(peer)
        ring = next_ring
    branches = defaultdict(list)
    for node_id, root in root_of.items():
        branches[root].append((node_id, depth[node_id]))
    return branches


def order_columns(graph, columns):
    """Order each column's node ids top to bottom so cables run as level as possible.

    Columns are placed busiest first. Each node then sorts by the average height of the ports it is cabled to
    in columns already placed, measured as a fraction of that column's height. Nodes with cables to columns
    not yet placed (switches with their own devices hanging off them) go below the rest, where those devices
    have room, and nodes with no placed cables go last. Ties keep rack order.
    """
    nodes = {node.id: node for node in graph.nodes.values()}
    by_column = defaultdict(list)
    for node in sorted(nodes.values(), key=rack_sort_key):
        by_column[columns[node.id]].append(node.id)
    placer = _ColumnPlacer(graph)
    busiest_first = sorted(
        by_column, key=lambda column: (-max(len(nodes[n].ports) for n in by_column[column]), abs(column), column)
    )
    return {column: placer.place(by_column[column]) for column in busiest_first}


class _ColumnPlacer:
    """Orders columns one at a time, remembering where placed ports sit."""

    def __init__(self, graph):
        self.rows = {}  # (node id, port id) -> row within its node, counting the header as row 0
        self.sizes = {}  # node id -> rows
        for node in graph.nodes.values():
            self.sizes[node.id] = len(node.ports) + 1
            for row, port in enumerate(node.sorted_ports(), start=1):
                self.rows[(node.id, port.id)] = row
        self.peers = defaultdict(list)
        for edge in graph.edges:
            self.peers[edge.a_node].append((edge.b_node, edge.b_port))
            self.peers[edge.b_node].append((edge.a_node, edge.a_port))
        self.heights = {}  # Placed node id -> (top row, its column's height in rows)

    def sort_key(self, node_id):
        """Fully placed peers first, then partly placed, then unplaced; each by average peer port height."""
        heights = [
            (self.heights[peer][0] + self.rows[(peer, port)]) / self.heights[peer][1]
            for peer, port in self.peers[node_id]
            if peer in self.heights
        ]
        if not heights:
            return (2, 0)
        return (int(len(heights) < len(self.peers[node_id])), sum(heights) / len(heights))

    def place(self, node_ids):
        """Order one column's node ids and record their heights."""
        ordered = sorted(node_ids, key=self.sort_key)
        total = sum(self.sizes[node_id] for node_id in ordered)
        top = 0
        for node_id in ordered:
            self.heights[node_id] = (top, total)
            top += self.sizes[node_id]
        return ordered


def rack_sort_key(node):
    """Order nodes as they sit in their rack: by rack, top unit first; unracked nodes last by name."""
    if node.position is None:
        return (1, "", 0, node.label)
    return (0, node.rack, -node.position, node.label)


@dataclass
class ScheduleRow:
    """One row of the cable schedule: a cable (or end-to-end path) from an A port to a B port."""

    a_node: Node
    a_port: Port
    b_node: Node
    b_port: Port
    cable: Cable
    via_patch_panel: bool


def cable_schedule(graph):
    """The graph's edges as ScheduleRows, in-scope end first, sorted by A device and port."""
    nodes = {node.id: node for node in graph.nodes.values()}
    ports = {(node.id, port.id): port for node in nodes.values() for port in node.ports.values()}
    rows = []
    for edge in graph.edges:
        a_node, b_node = nodes[edge.a_node], nodes[edge.b_node]
        a_port, b_port = ports[(edge.a_node, edge.a_port)], ports[(edge.b_node, edge.b_port)]
        if b_node.in_scope and not a_node.in_scope:
            a_node, a_port, b_node, b_port = b_node, b_port, a_node, a_port
        rows.append(ScheduleRow(a_node, a_port, b_node, b_port, edge.cable, edge.via_patch_panel))
    return sorted(rows, key=lambda row: (row.a_node.label, row.a_port.sort_key, row.b_node.label))
