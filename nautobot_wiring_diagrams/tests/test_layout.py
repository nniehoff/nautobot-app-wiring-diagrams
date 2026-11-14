"""Tests for column layout and the cable schedule, on graphs built without the database."""

from django.test import SimpleTestCase

from nautobot_wiring_diagrams.graph import Edge, Node, Port, WiringGraph, assign_columns, cable_schedule, order_columns
from nautobot_wiring_diagrams.render import PAGE_AUTO, PAGE_DIAGRAM, PAGE_SIZES, page_candidates, pick_page


def make_graph(cables, in_scope=()):
    """Build a WiringGraph from `[("dev-a port", "dev-b port"), ...]`; ports sort by name."""
    graph = WiringGraph()
    nodes = {}

    def end(spec):
        device, port_name = spec.split(" ")
        node = nodes.get(device)
        if node is None:
            node = nodes[device] = Node(
                id=f"n{len(nodes)}", label=device, subtitle="", url="", in_scope=device in in_scope
            )
            graph.nodes[device] = node
        port = node.ports.get(port_name)
        if port is None:
            port = node.ports[port_name] = Port(
                id=f"p{len(node.ports)}", name=port_name, url="", sort_key=(0, port_name)
            )
        return node, port

    for a_spec, b_spec in cables:
        (a_node, a_port), (b_node, b_port) = end(a_spec), end(b_spec)
        graph.edges.append(Edge(a_node.id, a_port.id, b_node.id, b_port.id, cable=None))
    return graph, nodes


class ColumnLayoutTestCase(SimpleTestCase):
    """assign_columns and order_columns."""

    def columns_by_label(self, graph, nodes):
        """Map device name to its column."""
        columns = assign_columns(graph)
        return {label: columns[node.id] for label, node in nodes.items()}

    def test_star_puts_busiest_device_in_the_middle(self):
        """A switch goes in column 0 and its devices split evenly either side."""
        graph, nodes = make_graph([(f"sw p{i}", f"host{i} eth0") for i in range(4)])
        columns = self.columns_by_label(graph, nodes)
        self.assertEqual(columns["sw"], 0)
        self.assertEqual(sorted(columns[f"host{i}"] for i in range(4)), [-1, -1, 1, 1])

    def test_devices_further_out_follow_their_switch(self):
        """Devices behind an access switch go one column further out, on the switch's side."""
        cables = [(f"core p{i}", f"srv{i} eth0") for i in range(6)]
        cables += [("core p9", "access p1"), ("access p2", "ap eth0"), ("access p3", "cam eth0")]
        graph, nodes = make_graph(cables)
        columns = self.columns_by_label(graph, nodes)
        self.assertEqual(columns["core"], 0)
        self.assertEqual(abs(columns["access"]), 1)
        self.assertEqual(columns["ap"], 2 * columns["access"])
        self.assertEqual(columns["cam"], 2 * columns["access"])

    def test_redundant_pair_brackets_dual_homed_devices(self):
        """Two equally busy switches go either side of the servers cabled to both."""
        cables = []
        for i in range(3):
            cables += [(f"spine-1 p{i}", f"srv{i} eth0"), (f"spine-2 p{i}", f"srv{i} eth1")]
        cables += [("spine-1 p9", "only-a eth0"), ("spine-2 p9", "only-b eth0")]
        graph, nodes = make_graph(cables)
        columns = self.columns_by_label(graph, nodes)
        self.assertEqual(columns["spine-1"], -1)
        self.assertEqual(columns["spine-2"], 1)
        self.assertEqual({columns[f"srv{i}"] for i in range(3)}, {0})
        self.assertEqual(columns["only-a"], -2)
        self.assertEqual(columns["only-b"], 2)

    def test_pair_makes_room_for_devices_behind_dual_homed_switches(self):
        """Devices behind a dual-homed switch sit between it and the pair."""
        cables = [("spine-1 p1", "access up1"), ("spine-2 p1", "access up2"), ("access p1", "ap eth0")]
        cables += [(f"spine-{n} p{i}", f"srv{i} eth{n}") for n in (1, 2) for i in range(2, 6)]
        graph, nodes = make_graph(cables)
        columns = self.columns_by_label(graph, nodes)
        self.assertEqual((columns["spine-1"], columns["spine-2"]), (-2, 2))
        self.assertEqual(columns["access"], 0)
        self.assertEqual(abs(columns["ap"]), 1)

    def test_order_follows_switch_ports(self):
        """Devices sort by the switch port they are cabled to, not by name."""
        graph, nodes = make_graph([("sw p1", "zed eth0"), ("sw p2", "alpha eth0"), ("sw p3", "mike eth0")])
        columns = {node_id: 0 if node_id == nodes["sw"].id else 1 for node_id in (n.id for n in nodes.values())}
        order = order_columns(graph, columns)
        labels = {node.id: node.label for node in nodes.values()}
        self.assertEqual([labels[node_id] for node_id in order[1]], ["zed", "alpha", "mike"])

    def test_order_puts_switches_with_their_own_devices_last(self):
        """A device that has further cables of its own sorts below devices cabled only to placed columns."""
        cables = [("sw p1", "access up"), ("access p1", "ap eth0"), ("sw p2", "srv eth0")]
        graph, nodes = make_graph(cables)
        columns = {nodes["sw"].id: 0, nodes["access"].id: 1, nodes["srv"].id: 1, nodes["ap"].id: 2}
        order = order_columns(graph, columns)
        self.assertEqual(order[1], [nodes["srv"].id, nodes["access"].id])


class CableScheduleTestCase(SimpleTestCase):
    """cable_schedule."""

    def test_in_scope_end_first(self):
        """Rows start from the in-scope device and sort by device then port."""
        graph, _ = make_graph([("remote eth0", "local p2"), ("local p1", "other eth0")], in_scope={"local"})
        rows = cable_schedule(graph)
        self.assertEqual(
            [(row.a_node.label, row.a_port.name, row.b_node.label) for row in rows],
            [("local", "p1", "other"), ("local", "p2", "remote")],
        )


class PageSizeTestCase(SimpleTestCase):
    """page_candidates and pick_page."""

    def test_diagram_size_has_no_pages(self):
        """The default keeps one page the diagram's size."""
        self.assertEqual(page_candidates(PAGE_DIAGRAM), [])
        self.assertIsNone(pick_page(500, 300, page_candidates(PAGE_DIAGRAM)))

    def test_page_turns_to_match_the_diagram(self):
        """Wide diagrams get a landscape page, tall ones portrait."""
        letter = page_candidates("letter")
        self.assertEqual(pick_page(500, 300, letter), (792, 612, 1))
        self.assertEqual(pick_page(300, 500, letter), (612, 792, 1))

    def test_large_diagram_scales_down_to_fit_inside_the_margins(self):
        """A diagram bigger than the page is scaled to the page less its margins."""
        page_width, page_height, scale = pick_page(1440, 600, page_candidates("letter"))
        self.assertEqual((page_width, page_height), (792, 612))
        self.assertAlmostEqual(scale, (792 - 72) / 1440)

    def test_auto_takes_the_smallest_page_that_fits_at_full_size(self):
        """Auto steps from Letter to Legal to Ledger."""
        auto = page_candidates(PAGE_AUTO)
        self.assertEqual(pick_page(700, 500, auto), (792, 612, 1))
        self.assertEqual(pick_page(900, 500, auto), (1008, 612, 1))
        self.assertEqual(pick_page(1100, 700, auto), (1224, 792, 1))

    def test_auto_scales_the_largest_page_when_nothing_fits(self):
        """Past Ledger, the diagram is scaled down onto Ledger."""
        page_width, page_height, scale = pick_page(3000, 1000, page_candidates(PAGE_AUTO))
        self.assertEqual((page_width, page_height), PAGE_SIZES["ledger"][::-1])
        self.assertLess(scale, 1)
