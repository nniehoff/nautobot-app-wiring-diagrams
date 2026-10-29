"""Forms for nautobot_wiring_diagrams."""

from django import forms
from nautobot.apps.forms import (
    BootstrapMixin,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    StaticSelect2,
    StaticSelect2Multiple,
)
from nautobot.dcim.choices import CableTypeChoices
from nautobot.dcim.models import Device, Location, Rack
from nautobot.extras.models import Status

from nautobot_wiring_diagrams.graph import CONNECTION_KINDS, DEFAULT_KINDS, DiagramOptions
from nautobot_wiring_diagrams.render import (
    ARRANGE_CHOICES,
    ARRANGE_COLUMNS,
    COLOR_BY_CABLE,
    COLOR_BY_CHOICES,
    ORDER_CABLES,
    ORDER_CHOICES,
    RANKDIR_CHOICES,
)

KIND_CHOICES = tuple((kind, kind.title()) for kind in CONNECTION_KINDS)


class WiringDiagramOptionsForm(BootstrapMixin, forms.Form):
    """Filter and display options for a wiring diagram (bound to GET parameters)."""

    cable_type = forms.MultipleChoiceField(
        choices=CableTypeChoices,
        label="Cable type",
        required=False,
        widget=StaticSelect2Multiple(),
    )
    status = DynamicModelMultipleChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "dcim.cable"},
        required=False,
    )
    kind = forms.MultipleChoiceField(
        choices=KIND_CHOICES,
        help_text="Defaults to data and console",
        initial=list(DEFAULT_KINDS),
        label="Connections",
        required=False,
        widget=StaticSelect2Multiple(),
    )
    collapse_patch_panels = forms.BooleanField(
        help_text="Draw end-to-end connections instead of each patch panel hop",
        required=False,
    )
    arrange = forms.ChoiceField(
        choices=ARRANGE_CHOICES,
        help_text="Columns put the busiest devices in the middle and their peers beside them",
        required=False,
        widget=StaticSelect2(),
    )
    order = forms.ChoiceField(
        choices=ORDER_CHOICES,
        help_text="Order of devices within each column",
        label="Order by",
        required=False,
        widget=StaticSelect2(),
    )
    group_by_rack = forms.BooleanField(
        help_text="Box each rack's devices; only drawn with two or more racks",
        initial=True,
        required=False,
    )
    color_by = forms.ChoiceField(choices=COLOR_BY_CHOICES, required=False, widget=StaticSelect2())
    rankdir = forms.ChoiceField(choices=RANKDIR_CHOICES, label="Direction", required=False, widget=StaticSelect2())

    def get_options(self):
        """Return `(DiagramOptions, render kwargs)` from cleaned data, or defaults if unbound or invalid."""
        if not self.is_bound or not self.is_valid():
            return DiagramOptions(), {
                "arrange": ARRANGE_COLUMNS,
                "color_by": COLOR_BY_CABLE,
                "group_by_rack": True,
                "order": ORDER_CABLES,
                "rankdir": None,
            }
        data = self.cleaned_data
        options = DiagramOptions(
            cable_types=data["cable_type"],
            statuses=list(data["status"] or []),
            kinds=data["kind"] or list(DEFAULT_KINDS),
            collapse_patch_panels=data["collapse_patch_panels"],
        )
        render_kwargs = {
            "arrange": data["arrange"] or ARRANGE_COLUMNS,
            "order": data["order"] or ORDER_CABLES,
            "color_by": data["color_by"] or COLOR_BY_CABLE,
            "rankdir": data["rankdir"] or None,
            # Checkboxes are absent from GET when unchecked, so only honor it once the form was submitted.
            "group_by_rack": data["group_by_rack"] if "rankdir" in self.data else True,
        }
        return options, render_kwargs


class WiringDiagramScopeForm(WiringDiagramOptionsForm):
    """Options form plus a Location, Rack, or Device picker for the standalone page."""

    location = DynamicModelChoiceField(queryset=Location.objects.all(), required=False)
    rack = DynamicModelChoiceField(queryset=Rack.objects.all(), query_params={"location": "$location"}, required=False)
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(), query_params={"location": "$location", "rack": "$rack"}, required=False
    )

    field_order = ["location", "rack", "device"]

    def get_scope(self):
        """Return the most specific object chosen (Device, then Rack, then Location), or None."""
        if not self.is_bound or not self.is_valid():
            return None
        return self.cleaned_data["device"] or self.cleaned_data["rack"] or self.cleaned_data["location"]
