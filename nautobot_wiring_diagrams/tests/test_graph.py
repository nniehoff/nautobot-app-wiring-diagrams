"""Tests for building and rendering wiring graphs."""

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from nautobot.apps.testing import TestCase
from nautobot.dcim.choices import CableTypeChoices
from nautobot.dcim.models import (
    Cable,
    Device,
    DeviceType,
    FrontPort,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Rack,
    RearPort,
)
from nautobot.extras.models import Role, Status

from nautobot_wiring_diagrams.graph import DiagramOptions, build_graph
from nautobot_wiring_diagrams.render import COLOR_BY_TYPE, to_dot


class WiringGraphTestCase(TestCase):
    """Build graphs from a small site: two switches, a server, and two patch panels."""

    @classmethod
    def setUpTestData(cls):  # pylint: disable=too-many-locals
        """Create the site, devices, and cables."""
        location_type = LocationType.objects.create(name="Wiring Site")
        location_type.content_types.add(
            ContentType.objects.get_for_model(Device), ContentType.objects.get_for_model(Rack)
        )
        active = Status.objects.get_for_model(Location).first()
        cls.location = Location.objects.create(name="Wiring HQ", location_type=location_type, status=active)
        cls.other_location = Location.objects.create(name="Elsewhere", location_type=location_type, status=active)
        rack_status = Status.objects.get_for_model(Rack).first()
        cls.rack = Rack.objects.create(name="R1", location=cls.location, status=rack_status)

        manufacturer = Manufacturer.objects.create(name="Wiring Co")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Box 9000")
        role = Role.objects.create(name="Wiring Role")
        role.content_types.add(ContentType.objects.get_for_model(Device))
        device_status = Status.objects.get_for_model(Device).first()
        interface_status = Status.objects.get_for_model(Interface).first()

        def device(name, location, rack=None):
            return Device.objects.create(
                name=name, device_type=device_type, role=role, status=device_status, location=location, rack=rack
            )

        cls.switch = device("sw1", cls.location, cls.rack)
        cls.server = device("srv1", cls.location, cls.rack)
        cls.remote = device("sw-remote", cls.other_location)
        panel_a = device("pp-a", cls.location, cls.rack)
        panel_b = device("pp-b", cls.other_location)

        def interface(dev, name):
            return Interface.objects.create(device=dev, name=name, type="1000base-t", status=interface_status)

        cable_status = Status.objects.get_for_model(Cable).get(name="Connected")
        cls.copper = Cable.objects.create(
            termination_a=interface(cls.switch, "eth1"),
            termination_b=interface(cls.server, "eth0"),
            status=cable_status,
            type=CableTypeChoices.TYPE_CAT6,
            color="ff0000",
        )

        # sw1 eth2 -> pp-a front 1 | pp-a rear 1 == trunk == pp-b rear 1 | pp-b front 1 -> sw-remote eth1
        rear_a = RearPort.objects.create(device=panel_a, name="Rear 1", type="lc", positions=1)
        rear_b = RearPort.objects.create(device=panel_b, name="Rear 1", type="lc", positions=1)
        front_a = FrontPort.objects.create(
            device=panel_a, name="Front 1", type="lc", rear_port=rear_a, rear_port_position=1
        )
        front_b = FrontPort.objects.create(
            device=panel_b, name="Front 1", type="lc", rear_port=rear_b, rear_port_position=1
        )
        Cable.objects.create(
            termination_a=interface(cls.switch, "eth2"),
            termination_b=front_a,
            status=cable_status,
            type=CableTypeChoices.TYPE_SMF,
        )
        Cable.objects.create(
            termination_a=rear_a, termination_b=rear_b, status=cable_status, type=CableTypeChoices.TYPE_SMF
        )
        Cable.objects.create(
            termination_a=front_b,
            termination_b=interface(cls.remote, "eth1"),
            status=cable_status,
            type=CableTypeChoices.TYPE_SMF,
        )

    def node_labels(self, graph):
        """Labels of all nodes in a graph."""
        return {node.label for node in graph.nodes.values()}

    def test_device_scope(self):
        """A device diagram includes the device and its cable peers only."""
        graph = build_graph(self.server)
        self.assertEqual(self.node_labels(graph), {"srv1", "sw1"})
        self.assertEqual(len(graph.edges), 1)

    def test_rack_scope_shows_patch_panel_hops(self):
        """By default every hop through a patch panel is a separate edge."""
        graph = build_graph(self.rack)
        self.assertEqual(self.node_labels(graph), {"sw1", "srv1", "pp-a", "pp-b"})
        # copper, sw1->pp-a, and the pp-a<->pp-b trunk; pp-b->sw-remote has no end in the rack.
        self.assertEqual(len(graph.edges), 3)

    def test_location_scope_includes_child_locations(self):
        """A location diagram covers devices in child Locations too."""
        child = Location.objects.create(
            name="Wiring Floor",
            location_type=self.location.location_type,
            parent=self.location,
            status=self.location.status,
        )
        self.remote.location = child
        self.remote.validated_save()
        graph = build_graph(self.location)
        self.assertIn("sw-remote", self.node_labels(graph))

    def test_collapse_patch_panels(self):
        """Collapsing replaces the panel hops with one end-to-end edge."""
        graph = build_graph(self.switch, DiagramOptions(collapse_patch_panels=True))
        self.assertEqual(self.node_labels(graph), {"sw1", "srv1", "sw-remote"})
        self.assertEqual(len(graph.edges), 2)
        self.assertEqual(sum(edge.via_patch_panel for edge in graph.edges), 1)

    def test_cable_type_filter(self):
        """Only cables of the selected types are drawn."""
        graph = build_graph(self.rack, DiagramOptions(cable_types=[CableTypeChoices.TYPE_CAT6]))
        self.assertEqual([edge.cable for edge in graph.edges], [self.copper])

    def test_connection_kind_filter(self):
        """Excluding data connections leaves nothing for an all-data site."""
        graph = build_graph(self.rack, DiagramOptions(kinds=["power"]))
        self.assertEqual(graph.edges, [])

    @override_settings(PLUGINS_CONFIG={"nautobot_wiring_diagrams": {"cable_type_colors": {"cat6": "00ff00"}}})
    def test_dot_colors(self):
        """Cable color wins by default; type color wins when coloring by type."""
        graph = build_graph(self.server)
        self.assertIn('color="#ff0000"', to_dot(graph).source)
        by_type = to_dot(graph, color_by=COLOR_BY_TYPE).source
        self.assertIn('color="#00ff00"', by_type)
        self.assertIn("legend", by_type)
        self.assertIn(">CAT6<", by_type)

    def test_dot_escapes_names(self):
        """Names are escaped inside HTML-like labels."""
        self.server.name = "srv<&>"
        self.server.validated_save()
        source = to_dot(build_graph(self.server)).source
        self.assertIn("srv&lt;&amp;&gt;", source)


class WiringDiagramViewTestCase(TestCase):
    """Smoke tests for the views."""

    @classmethod
    def setUpTestData(cls):
        """Create a location to view."""
        location_type = LocationType.objects.create(name="View Site")
        cls.location = Location.objects.create(
            name="View HQ", location_type=location_type, status=Status.objects.get_for_model(Location).first()
        )

    def setUp(self):
        """Log in as a superuser."""
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

    def test_location_tab(self):
        """The tab renders with no cables."""
        url = reverse("plugins:nautobot_wiring_diagrams:location_wiring_diagram_tab", kwargs={"pk": self.location.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No cables match these options.")

    def test_standalone_page(self):
        """The picker page renders."""
        response = self.client.get(reverse("plugins:nautobot_wiring_diagrams:wiring_diagram"))
        self.assertEqual(response.status_code, 200)

    def test_export_dot(self):
        """DOT export needs no Graphviz binary and is returned as an attachment."""
        url = reverse("plugins:nautobot_wiring_diagrams:export", kwargs={"scope": "location", "pk": self.location.pk})
        response = self.client.get(url, {"format": "dot"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"graph wiring"))

    def test_export_bad_format(self):
        """Unknown formats are rejected."""
        url = reverse("plugins:nautobot_wiring_diagrams:export", kwargs={"scope": "location", "pk": self.location.pk})
        self.assertEqual(self.client.get(url, {"format": "exe"}).status_code, 400)

    def test_export_bad_scope(self):
        """Unknown scopes are 404."""
        url = reverse("plugins:nautobot_wiring_diagrams:export", kwargs={"scope": "circuit", "pk": self.location.pk})
        self.assertEqual(self.client.get(url).status_code, 404)
