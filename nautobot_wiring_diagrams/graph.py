"""Build a wiring graph for a Location, Rack, or Device from Nautobot cables."""

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
    kinds: list = field(default_factory=lambda: list(CONNECTION_KINDS))
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
class Node:
    """A device, circuit, or power panel in the diagram."""

    id: str
    label: str
    subtitle: str
    url: str
    in_scope: bool
    group: str = ""
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
