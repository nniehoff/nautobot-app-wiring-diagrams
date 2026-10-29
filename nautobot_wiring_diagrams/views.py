"""Views for nautobot_wiring_diagrams."""

import csv
import io

import graphviz
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from nautobot.apps.views import GenericView, ObjectView
from nautobot.dcim.models import Device, Location, Rack

from nautobot_wiring_diagrams.forms import WiringDiagramOptionsForm, WiringDiagramScopeForm
from nautobot_wiring_diagrams.graph import build_graph, cable_schedule
from nautobot_wiring_diagrams.render import EXPORT_FORMATS, app_settings, render_diagram, render_inline_svg, to_dot

SCOPE_MODELS = {"location": Location, "rack": Rack, "device": Device}


def scope_name(scope_obj):
    """URL scope segment for a Location, Rack, or Device."""
    return scope_obj._meta.model_name


def diagram_context(request, scope_obj, form):
    """Build the graph for `scope_obj` and return template context with the rendered SVG or an error."""
    options, render_kwargs = form.get_options()
    graph = build_graph(scope_obj, options, user=request.user)
    query = request.GET.copy()
    query.pop("format", None)
    context = {
        "diagram_scope": scope_obj,
        "export_url": reverse(
            "plugins:nautobot_wiring_diagrams:export", kwargs={"scope": scope_name(scope_obj), "pk": scope_obj.pk}
        ),
        "export_query": query.urlencode(),
        # CSV is the cable schedule; its button sits on the schedule card.
        "export_formats": [fmt for fmt in EXPORT_FORMATS if fmt != "csv"],
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "schedule": cable_schedule(graph),
    }
    max_nodes = app_settings().get("max_nodes", 500)
    if len(graph.nodes) > max_nodes:
        context["diagram_error"] = (
            f"This diagram has {len(graph.nodes)} nodes, more than the configured maximum of {max_nodes}. "
            "Narrow the scope or filters, or export the diagram instead."
        )
    elif graph.edges:
        try:
            context["diagram_svg"] = mark_safe(  # noqa: S308 - Graphviz output; labels are escaped in render.py
                render_inline_svg(to_dot(graph, **render_kwargs))
            )
        except graphviz.ExecutableNotFound:
            context["diagram_error"] = "Graphviz is not installed on the Nautobot server (`dot` is missing)."
    return context


class WiringDiagramTabView(ObjectView):
    """Base view for the "Wiring Diagram" tab on a Location, Rack, or Device."""

    template_name = "nautobot_wiring_diagrams/object_wiring_diagram.html"

    def get_extra_context(self, request, instance):
        """Add the diagram and options form."""
        form = WiringDiagramOptionsForm(request.GET or None)
        return {"options_form": form, **diagram_context(request, instance, form)}


class LocationWiringDiagramView(WiringDiagramTabView):
    """Wiring Diagram tab for a Location (includes child Locations)."""

    queryset = Location.objects.all()


class RackWiringDiagramView(WiringDiagramTabView):
    """Wiring Diagram tab for a Rack."""

    queryset = Rack.objects.all()


class DeviceWiringDiagramView(WiringDiagramTabView):
    """Wiring Diagram tab for a Device."""

    queryset = Device.objects.all()


class WiringDiagramView(GenericView):
    """Standalone page: pick a Location, Rack, or Device and view its wiring diagram."""

    template_name = "nautobot_wiring_diagrams/wiring_diagram.html"

    def get(self, request):
        """Render the picker and, once a scope is chosen, the diagram."""
        form = WiringDiagramScopeForm(request.GET or None)
        context = {"options_form": form, "title": "Wiring Diagrams"}
        scope_obj = form.get_scope()
        if scope_obj is not None:
            model = type(scope_obj)
            if not model.objects.restrict(request.user, "view").filter(pk=scope_obj.pk).exists():
                raise Http404
            context.update(diagram_context(request, scope_obj, form))
        return render(request, self.template_name, context)


class WiringDiagramExportView(GenericView):
    """Download a wiring diagram as PDF, SVG, PNG, or Graphviz DOT source."""

    def get(self, request, scope, pk):
        """Render the diagram in the requested `format` (default PDF) as an attachment."""
        model = SCOPE_MODELS.get(scope)
        if model is None:
            raise Http404
        scope_obj = get_object_or_404(model.objects.restrict(request.user, "view"), pk=pk)
        fmt = request.GET.get("format", "pdf")
        if fmt not in EXPORT_FORMATS:
            return HttpResponseBadRequest(f"Unsupported format {fmt!r}; choose one of {', '.join(EXPORT_FORMATS)}.")
        form = WiringDiagramOptionsForm(request.GET)
        options, render_kwargs = form.get_options()
        graph = build_graph(scope_obj, options, user=request.user)
        if fmt == "csv":
            data = schedule_csv(cable_schedule(graph))
        else:
            dot = to_dot(graph, title=f"{scope_obj} wiring diagram", **render_kwargs)
            try:
                data = render_diagram(dot, fmt)
            except graphviz.ExecutableNotFound:
                return HttpResponse("Graphviz is not installed on the Nautobot server.", status=501)
        response = HttpResponse(data, content_type=EXPORT_FORMATS[fmt])
        filename = f"{slugify(str(scope_obj)) or scope}-wiring.{fmt}"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


SCHEDULE_COLUMNS = (
    "Device A",
    "Port A",
    "Device B",
    "Port B",
    "Cable",
    "Type",
    "Color",
    "Status",
    "Length",
    "Via patch panel",
)


def schedule_csv(rows):
    """Render cable schedule rows as CSV bytes."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(SCHEDULE_COLUMNS)
    for row in rows:
        cable = row.cable
        writer.writerow(
            (
                row.a_node.label,
                row.a_port.name,
                row.b_node.label,
                row.b_port.name,
                str(cable),
                cable.get_type_display() if cable.type else "",
                f"#{cable.color}" if cable.color else "",
                str(cable.status) if cable.status_id else "",
                f"{cable.length} {cable.length_unit}".strip() if cable.length else "",
                "yes" if row.via_patch_panel else "",
            )
        )
    return output.getvalue().encode()
