"""Render a WiringGraph with Graphviz."""

from html import escape

import graphviz
from django.conf import settings
from nautobot.dcim.choices import CableTypeChoices

FONT = "Helvetica"
IN_SCOPE_HEADER = "#cfe2ff"
OUT_OF_SCOPE_HEADER = "#e9ecef"
STATUS_STYLES = {"planned": "dashed", "decommissioning": "dotted"}

COLOR_BY_CABLE = "cable"
COLOR_BY_TYPE = "type"
COLOR_BY_CHOICES = (
    (COLOR_BY_CABLE, "Cable color, then type"),
    (COLOR_BY_TYPE, "Cable type"),
)
RANKDIR_CHOICES = (("LR", "Left to right"), ("TB", "Top to bottom"))

EXPORT_FORMATS = {
    "pdf": "application/pdf",
    "svg": "image/svg+xml",
    "png": "image/png",
    "dot": "text/vnd.graphviz",
}


def app_settings():
    """Return this app's settings with defaults applied."""
    return settings.PLUGINS_CONFIG.get("nautobot_wiring_diagrams", {})


def normalize_color(value):
    """Return a `#rrggbb` color, or "" if `value` is empty."""
    if not value:
        return ""
    return value if value.startswith("#") else f"#{value}"


def edge_color(cable, color_by, type_colors, default_color):
    """Pick the line color for a cable."""
    if color_by == COLOR_BY_CABLE and cable.color:
        return normalize_color(cable.color)
    return normalize_color(type_colors.get(cable.type, "")) or default_color


def _node_label(node):
    """Graphviz HTML-like label: a header cell then one cell per port."""
    header = IN_SCOPE_HEADER if node.in_scope else OUT_OF_SCOPE_HEADER
    subtitle = f'<BR/><FONT POINT-SIZE="9">{escape(node.subtitle)}</FONT>' if node.subtitle else ""
    rows = [
        f'<TR><TD BGCOLOR="{header}" HREF="{escape(node.url)}" TITLE="{escape(node.label)}">'
        f"<B>{escape(node.label)}</B>{subtitle}</TD></TR>"
    ]
    for port in node.sorted_ports():
        rows.append(
            f'<TR><TD PORT="{port.id}" ALIGN="LEFT" HREF="{escape(port.url)}" TITLE="{escape(port.name)}">'
            f"{escape(port.name)}</TD></TR>"
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


def to_dot(wiring_graph, *, title="", color_by=COLOR_BY_CABLE, rankdir=None, group_by_rack=True):
    """Convert a WiringGraph into a `graphviz.Graph`."""
    config = app_settings()
    type_colors = config.get("cable_type_colors", {})
    default_color = normalize_color(config.get("default_cable_color", "#6c757d"))
    dot = graphviz.Graph(
        name="wiring",
        graph_attr={
            "bgcolor": "white",
            "fontname": FONT,
            "label": graphviz.nohtml(title),
            "labelloc": "t",
            "nodesep": "0.4",
            "rankdir": rankdir or config.get("default_rankdir", "LR"),
            "ranksep": "1.2",
            "splines": "spline",
        },
        node_attr={"fontname": FONT, "fontsize": "10", "shape": "plaintext"},
        edge_attr={"fontname": FONT, "fontsize": "9", "penwidth": "2"},
    )

    _add_nodes(dot, wiring_graph, group_by_rack)
    used_types = _add_edges(dot, wiring_graph, color_by, type_colors, default_color)
    if used_types and color_by == COLOR_BY_TYPE:
        dot.node("legend", label=_legend(used_types, type_colors, default_color))
    return dot


def _add_nodes(dot, wiring_graph, group_by_rack):
    """Add nodes, inside a cluster per rack when grouping."""
    groups = {}
    for node in wiring_graph.nodes.values():
        groups.setdefault(node.group if group_by_rack else "", []).append(node)
    for index, (group, nodes) in enumerate(sorted(groups.items())):
        if not group:
            for node in nodes:
                dot.node(node.id, label=_node_label(node))
            continue
        with dot.subgraph(name=f"cluster_{index}") as cluster:
            cluster.attr(label=graphviz.nohtml(group), style="rounded,dashed", color="#adb5bd")
            for node in nodes:
                cluster.node(node.id, label=_node_label(node))


def _add_edges(dot, wiring_graph, color_by, type_colors, default_color):
    """Add one edge per graph edge; return the set of cable types drawn."""
    used_types = set()
    for edge in wiring_graph.edges:
        cable = edge.cable
        used_types.add(cable.type)
        style = STATUS_STYLES.get(cable.status.name.lower(), "solid") if cable.status_id else "solid"
        if edge.via_patch_panel:
            style = f"{style},bold"
        dot.edge(
            f"{edge.a_node}:{edge.a_port}",
            f"{edge.b_node}:{edge.b_port}",
            color=edge_color(cable, color_by, type_colors, default_color),
            label=graphviz.nohtml(cable.label),
            style=style,
            tooltip=graphviz.nohtml(_cable_tooltip(cable)),
            URL=cable.get_absolute_url(),
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
