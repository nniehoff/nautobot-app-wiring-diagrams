# Frequently Asked Questions

## The tab says "Graphviz is not installed on the Nautobot server"

Curved diagrams are drawn server-side by the Graphviz `dot` command, which is not a Python package. Install the `graphviz` system package on every Nautobot web server (`apt-get install graphviz` on Debian or Ubuntu, including images built from `networktocode/nautobot`) and restart Nautobot. Square lines (**Line style: Square with line jumps**) are laid out in the browser and work without it, but the export URL always uses Graphviz.

## The diagram says it has more nodes than the configured maximum

Diagrams with more than `max_nodes` nodes (default 500) are not drawn in the page, because the browser struggles with them. Narrow the scope (a Rack instead of a Location), filter by cable type or connection kind, or download the diagram instead: exports are not limited. An administrator can raise `max_nodes` in `PLUGINS_CONFIG`.

## Why are power cables missing?

Power is left out by default so data cabling stays readable. Add **Power** under **Connections** and select **Update**.

## Why do some devices have a gray header?

Blue headers are devices in the chosen scope. Gray headers are the far ends of their cables outside it, such as a switch in another rack. Only their cabled ports toward the scope are drawn.

## Why does a cable I can see in Nautobot not appear?

Diagrams only include objects you have permission to view, so a cable or device hidden from you by object permissions is left out. The **Cable types**, **Status** and **Connections** filters also hide cables.

## Why do square-line downloads differ from the export URL?

Square lines are laid out in the browser by ELK, so their PDF, SVG and PNG buttons save what is on screen. The export URL renders on the server with Graphviz and always draws curved lines.

## Does the app need migrations or a worker?

No. It adds no models and runs no jobs. `nautobot-server post_upgrade` is still needed after installing or upgrading, to collect its static files.
