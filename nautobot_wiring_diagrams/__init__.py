"""App declaration for nautobot_wiring_diagrams."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class WiringDiagramsConfig(NautobotAppConfig):
    """App configuration for the nautobot_wiring_diagrams app."""

    name = "nautobot_wiring_diagrams"
    verbose_name = "Nautobot Wiring Diagrams"
    version = __version__
    author = "Nick Niehoff"
    description = "Render wiring diagrams from Nautobot cables for a Location, Rack, or Device."
    base_url = "wiring-diagrams"
    min_version = "3.2.0"
    max_version = "3.9999"
    required_settings = []
    default_settings = {
        "cable_type_colors": {},
        "default_cable_color": "#6c757d",
        "default_rankdir": "LR",
        "max_nodes": 500,
    }
    docs_view_name = "plugins:nautobot_wiring_diagrams:docs"
    searchable_models = []


config = WiringDiagramsConfig  # pylint:disable=invalid-name
