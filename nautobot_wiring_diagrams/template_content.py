"""Add a "Wiring Diagram" tab to Location, Rack, and Device detail views."""

from nautobot.apps.ui import DistinctViewTab, TemplateExtension


class WiringDiagramTab(DistinctViewTab):
    """Tab linking to the wiring diagram view for this object."""

    def __init__(self, model_name, **kwargs):
        """Create the tab for `model_name` ("location", "rack", or "device")."""
        super().__init__(
            label="Wiring Diagram",
            tab_id="wiring_diagram_tab",
            weight=1100,
            url_name=f"plugins:nautobot_wiring_diagrams:{model_name}_wiring_diagram_tab",
            required_permissions=["dcim.view_cable"],
            **kwargs,
        )


class LocationWiringDiagram(TemplateExtension):  # pylint: disable=abstract-method
    """Location detail view extension."""

    model = "dcim.location"
    object_detail_tabs = [WiringDiagramTab("location")]


class RackWiringDiagram(TemplateExtension):  # pylint: disable=abstract-method
    """Rack detail view extension."""

    model = "dcim.rack"
    object_detail_tabs = [WiringDiagramTab("rack")]


class DeviceWiringDiagram(TemplateExtension):  # pylint: disable=abstract-method
    """Device detail view extension."""

    model = "dcim.device"
    object_detail_tabs = [WiringDiagramTab("device")]


template_extensions = (LocationWiringDiagram, RackWiringDiagram, DeviceWiringDiagram)
