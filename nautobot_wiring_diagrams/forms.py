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

from nautobot_wiring_diagrams.graph import CONNECTION_KINDS, DiagramOptions
from nautobot_wiring_diagrams.render import COLOR_BY_CABLE, COLOR_BY_CHOICES, RANKDIR_CHOICES

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
        help_text="Defaults to all",
        label="Connections",
        required=False,
        widget=StaticSelect2Multiple(),
    )
    collapse_patch_panels = forms.BooleanField(
        help_text="Draw end-to-end connections instead of each patch panel hop",
        required=False,
    )
    group_by_rack = forms.BooleanField(initial=True, required=False)
    color_by = forms.ChoiceField(choices=COLOR_BY_CHOICES, required=False, widget=StaticSelect2())
    rankdir = forms.ChoiceField(choices=RANKDIR_CHOICES, label="Layout", required=False, widget=StaticSelect2())

    def get_options(self):
        """Return `(DiagramOptions, render kwargs)` from cleaned data, or defaults if unbound or invalid."""
        if not self.is_bound or not self.is_valid():
            return DiagramOptions(), {"color_by": COLOR_BY_CABLE, "rankdir": None, "group_by_rack": True}
        data = self.cleaned_data
        options = DiagramOptions(
            cable_types=data["cable_type"],
            statuses=list(data["status"] or []),
            kinds=data["kind"] or list(CONNECTION_KINDS),
            collapse_patch_panels=data["collapse_patch_panels"],
        )
        render_kwargs = {
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
