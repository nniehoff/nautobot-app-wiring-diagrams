"""Render a WiringGraph with Graphviz."""

from html import escape

import graphviz
from django.conf import settings
from nautobot.dcim.choices import CableTypeChoices

from nautobot_wiring_diagrams.graph import assign_columns, order_columns, rack_sort_key

FONT = "Helvetica"
IN_SCOPE_HEADER = "#cfe2ff"
OUT_OF_SCOPE_HEADER = "#e9ecef"
STATUS_STYLES = {"planned": "dashed", "decommissioning": "dotted"}

COLOR_BY_CABLE = "cable"
COLOR_BY_TYPE = "type"
COLOR_BY_DEVICE = "device"
COLOR_BY_CHOICES = (
    (COLOR_BY_CABLE, "Cable color, then type, then device"),
    (COLOR_BY_TYPE, "Cable type"),
    (COLOR_BY_DEVICE, "Busier device"),
)
# Tableau 10 without its gray and olive: distinct on white, and none close to the default cable gray.
DEVICE_PALETTE = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf")
RANKDIR_CHOICES = (("LR", "Left to right"), ("TB", "Top to bottom"))
ARRANGE_COLUMNS = "columns"
ARRANGE_FREE = "free"
ARRANGE_CHOICES = (
    (ARRANGE_COLUMNS, "Columns by cabled ports"),
    (ARRANGE_FREE, "Graphviz default"),
)
ORDER_CABLES = "cables"
ORDER_RACK = "rack"
ORDER_CHOICES = (
    (ORDER_CABLES, "Keep cables level"),
    (ORDER_RACK, "Rack position"),
)
# Ports a cable leaves from and enters, for each direction: toward the next column, then away from it.
FACING_PORTS = {"LR": ("e", "w"), "TB": ("s", "n")}

EXPORT_FORMATS = {
    "pdf": "application/pdf",
    "svg": "image/svg+xml",
    "png": "image/png",
    "dot": "text/vnd.graphviz",
    # The cable schedule, not the drawing.
    "csv": "text/csv",
}


def app_settings():
    """Return this app's settings with defaults applied."""
    return settings.PLUGINS_CONFIG.get("nautobot_wiring_diagrams", {})


def normalize_color(value):
    """Return a `#rrggbb` color, or "" if `value` is empty."""
    if not value:
        return ""
    return value if value.startswith("#") else f"#{value}"


def edge_color(cable, color_by, type_colors, default_color, device_color=""):
    """Pick the line color for a cable; `device_color` is the busier end's palette color."""
    if color_by == COLOR_BY_DEVICE:
        return device_color or default_color
    if color_by == COLOR_BY_CABLE and cable.color:
        return normalize_color(cable.color)
    type_color = normalize_color(type_colors.get(cable.type, ""))
    if color_by == COLOR_BY_CABLE:
        return type_color or device_color or default_color
    return type_color or default_color


def device_colors(wiring_graph):
    """Map node id to a palette color, handing colors out busiest node first."""
    nodes = sorted(wiring_graph.nodes.values(), key=lambda node: (-len(node.ports), node.label, node.id))
    return {node.id: DEVICE_PALETTE[index % len(DEVICE_PALETTE)] for index, node in enumerate(nodes)}


def _node_label(node):
    """Graphviz HTML-like label: a header cell then one cell per port."""
    header = IN_SCOPE_HEADER if node.in_scope else OUT_OF_SCOPE_HEADER
    subtitle = f'<BR/><FONT POINT-SIZE="9">{escape(node.subtitle)}</FONT>' if node.subtitle else ""
    # IDs become `a_<ID>` groups in SVG output, which wiring-diagram.js uses to highlight cables on hover.
    rows = [
        f'<TR><TD BGCOLOR="{header}" HREF="{escape(node.url)}" TITLE="{escape(node.label)}" ID="wd-{node.id}">'
        f"<B>{escape(node.label)}</B>{subtitle}</TD></TR>"
    ]
    for port in node.sorted_ports():
        rows.append(
            f'<TR><TD PORT="{port.id}" ALIGN="LEFT" HREF="{escape(port.url)}" TITLE="{escape(port.name)}"'
            f' ID="wd-{node.id}-{port.id}">{escape(port.name)}</TD></TR>'
        )
    return f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">{"".join(rows)}</TABLE>>'


def _cable_tooltip(cable):
    parts = [str(cable)]
    if cable.type:
        parts.append(cable.get_type_display())
    if cable.length:
        parts.append(f"{cable.length} {cable.length_unit}".strip())
    if cable.status_id:
        parts.append(str(cable.status))
    return " | ".join(parts)


def _legend(used_types, type_colors, default_color):
    """HTML-like label listing the colors of cable types in use."""
    rows = ['<TR><TD COLSPAN="2"><B>Cable types</B></TD></TR>']
    labels = CableTypeChoices.as_dict()
    for cable_type in sorted(used_types):
        color = normalize_color(type_colors.get(cable_type, "")) or default_color
        name = labels.get(cable_type, "Unspecified") if cable_type else "Unspecified"
        rows.append(f'<TR><TD BGCOLOR="{color}" WIDTH="24"> </TD><TD ALIGN="LEFT">{escape(name)}</TD></TR>')
    return f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">{"".join(rows)}</TABLE>>'


def to_dot(  # pylint: disable=too-many-arguments
    wiring_graph,
    *,
    title="",
    color_by=COLOR_BY_CABLE,
    rankdir=None,
    group_by_rack=True,
    arrange=ARRANGE_COLUMNS,
    order=ORDER_CABLES,
):
    """Convert a WiringGraph into a `graphviz.Graph`."""
    config = app_settings()
    rankdir = rankdir or config.get("default_rankdir", "LR")
    dot = graphviz.Graph(
        name="wiring",
        graph_attr={
            "bgcolor": "white",
            "fontname": FONT,
            "label": graphviz.nohtml(title),
            "labelloc": "t",
            # Lets rank=same columns cut across the rack clusters.
            "newrank": "true",
            "nodesep": "0.4",
            "rankdir": rankdir,
            "ranksep": "1.2",
            "splines": "spline",
        },
        node_attr={"fontname": FONT, "fontsize": "10", "shape": "plaintext"},
        edge_attr={"fontname": FONT, "fontsize": "9", "penwidth": "2"},
    )

    columns = assign_columns(wiring_graph) if arrange == ARRANGE_COLUMNS else {}
    # A single rack's box adds nothing but pushes every device outside it to the top or bottom.
    group_by_rack = group_by_rack and len({node.group for node in wiring_graph.nodes.values() if node.group}) > 1
    _add_nodes(dot, wiring_graph, group_by_rack)
    if columns:
        _add_columns(dot, wiring_graph, columns, order)
    colors = {
        "type_colors": config.get("cable_type_colors", {}),
        "default_color": normalize_color(config.get("default_cable_color", "#6c757d")),
        "device_colors": device_colors(wiring_graph),
    }
    used_types = _add_edges(dot, wiring_graph, color_by, colors, columns, FACING_PORTS.get(rankdir, ("e", "w")))
    if used_types and color_by == COLOR_BY_TYPE:
        dot.node("legend", label=_legend(used_types, colors["type_colors"], colors["default_color"]))
    return dot


def _add_nodes(dot, wiring_graph, group_by_rack):
    """Add nodes, inside a cluster per rack when grouping, in rack order."""
    groups = {}
    for node in sorted(wiring_graph.nodes.values(), key=rack_sort_key):
        groups.setdefault(node.group if group_by_rack else "", []).append(node)
    for index, (group, nodes) in enumerate(sorted(groups.items())):
        if not group:
            for node in nodes:
                dot.node(node.id, label=_node_label(node), id=f"wd-{node.id}-node")
            continue
        with dot.subgraph(name=f"cluster_{index}") as cluster:
            cluster.attr(label=graphviz.nohtml(group), style="rounded,dashed", color="#adb5bd")
            for node in nodes:
                cluster.node(node.id, label=_node_label(node), id=f"wd-{node.id}-node")


def _add_columns(dot, wiring_graph, columns, order):
    """Pin each node to its column with a rank=same subgraph; a hidden chain of anchors keeps columns in order."""
    if order == ORDER_RACK:
        by_column, pinned = _rack_columns(wiring_graph, columns)
    else:
        by_column = pinned = order_columns(wiring_graph, columns)
    ordered = sorted(by_column)
    for column in ordered:
        with dot.subgraph(name=f"column_{column}") as subgraph:
            subgraph.attr(rank="same")
            subgraph.node(_anchor(column), label="", shape="point", style="invis", width="0", height="0")
            for node_id in by_column[column]:
                subgraph.node(node_id)
            # Flat invisible edges hold the column's order, top to bottom.
            for upper, lower in zip(pinned[column], pinned[column][1:]):
                subgraph.edge(upper, lower, style="invis")
    for left, right in zip(ordered, ordered[1:]):
        dot.edge(_anchor(left), _anchor(right), style="invis", minlen=str(right - left))


def _anchor(column):
    """Name of the hidden node that holds a column's place."""
    return f"column_{column}".replace("-", "m")


def _rack_columns(wiring_graph, columns):
    """Each column's node ids in rack order, and the racked ones to pin in that order."""
    nodes = {node.id: node for node in wiring_graph.nodes.values()}
    by_column = {}
    for node in sorted(nodes.values(), key=rack_sort_key):
        by_column.setdefault(columns[node.id], []).append(node.id)
    # Only racked devices have a position to keep; the rest go wherever crosses fewest cables.
    pinned = {
        column: [node_id for node_id in node_ids if nodes[node_id].position is not None]
        for column, node_ids in by_column.items()
    }
    return by_column, pinned


def _edge_ends(edge, columns, facing):
    """Graphviz tail and head (`node:port[:side]`) for an edge, and its layout and hover attributes."""
    tail, head = (edge.a_node, edge.a_port), (edge.b_node, edge.b_port)
    # Read by wiring-diagram.js to light up a cable and both of its ends.
    attrs = {"class": f"wd-{tail[0]} wd-{head[0]} wd-{tail[0]}-{tail[1]} wd-{head[0]}-{head[1]}"}
    if not columns:
        return f"{tail[0]}:{tail[1]}", f"{head[0]}:{head[1]}", attrs
    # Dot ranks undirected edges tail first, so point every edge outward from the lower column.
    if columns[tail[0]] > columns[head[0]]:
        tail, head = head, tail
    if columns[tail[0]] == columns[head[0]]:
        tail_side = head_side = facing[0]
        attrs["constraint"] = "false"
    else:
        tail_side, head_side = facing
    return f"{tail[0]}:{tail[1]}:{tail_side}", f"{head[0]}:{head[1]}:{head_side}", attrs


def _edge_style(edge):
    """Line style from the cable's status, bold when the edge stands for a path through patch panels."""
    cable = edge.cable
    style = STATUS_STYLES.get(cable.status.name.lower(), "solid") if cable.status_id else "solid"
    return f"{style},bold" if edge.via_patch_panel else style


def _edge_colors(wiring_graph, color_by, colors):
    """Line color of each edge, in order."""
    ports = {node.id: len(node.ports) for node in wiring_graph.nodes.values()}
    edge_colors = []
    for edge in wiring_graph.edges:
        busier = max((edge.a_node, edge.b_node), key=lambda node_id: (ports[node_id], node_id))
        edge_colors.append(
            edge_color(
                edge.cable, color_by, colors["type_colors"], colors["default_color"], colors["device_colors"][busier]
            )
        )
    return edge_colors


def _add_edges(dot, wiring_graph, color_by, colors, columns, facing):  # pylint: disable=too-many-arguments
    """Add one edge per graph edge; return the set of cable types drawn."""
    used_types = set()
    edge_colors = _edge_colors(wiring_graph, color_by, colors)
    for index, edge in enumerate(wiring_graph.edges):
        cable = edge.cable
        used_types.add(cable.type)
        tail_ref, head_ref, attrs = _edge_ends(edge, columns, facing)
        if edge.kind == "power":
            attrs["penwidth"] = "1"
        dot.edge(
            tail_ref,
            head_ref,
            color=edge_colors[index],
            label=graphviz.nohtml(cable.label),
            style=_edge_style(edge),
            tooltip=graphviz.nohtml(_cable_tooltip(cable)),
            URL=cable.get_absolute_url(),
            id=f"wd-e{index}",
            **attrs,
        )
    return used_types


def render_diagram(dot, fmt):
    """Render a Graphviz graph to bytes in `fmt` (one of EXPORT_FORMATS)."""
    if fmt == "dot":
        return dot.source.encode()
    return dot.pipe(format=fmt)


def render_inline_svg(dot):
    """Render to an SVG string suitable for embedding in HTML (no XML prolog or DOCTYPE)."""
    svg = render_diagram(dot, "svg").decode()
    return svg[svg.find("<svg") :]
