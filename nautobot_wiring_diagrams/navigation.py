"""Menu items for nautobot_wiring_diagrams."""

from nautobot.apps.ui import NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Devices",
        groups=(
            NavMenuGroup(
                name="Connections",
                weight=500,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_wiring_diagrams:wiring_diagram",
                        name="Wiring Diagrams",
                        permissions=["dcim.view_cable"],
                        weight=1000,
                    ),
                ),
            ),
        ),
    ),
)
