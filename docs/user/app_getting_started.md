# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md). Graphviz must be installed on the Nautobot server.

## First steps with the App

1. Open a Rack that has cabled devices in it.
2. Select the **Wiring Diagram** tab. The diagram shows each device in the rack with its cabled ports, and the far end of each cable. Data and console cables are shown; power is left out.
3. Drag or scroll to pan, and pinch or Ctrl+scroll to zoom. Hover a cable to highlight it and both of its ends, or hover a port or device name to highlight all of its cables.
4. Under **Options**, choose one or more **Cable types**, for example only Cat6, and select **Update**. Add **Power** under **Connections** to draw power cables too.
5. Select **PDF** above the diagram to download it with the same options.
6. Scroll down to the **Cable schedule** for the same cables as a table, and select **CSV** to download it.

The same tab is available on Locations (covering every device in the Location and its child Locations) and on Devices.

## What are the next steps?

- Set `cable_type_colors` in `PLUGINS_CONFIG` so each cable type has a consistent color. Then choose **Color by: Cable type** to add a legend to the diagram.
- Try **Collapse patch panels** to see end-to-end connections through your patch panels.
- Set **Order by: Rack position** to order devices as they sit in the rack instead of by the ports they are cabled to. Cables then cross more often.
- Set **Arrange: Graphviz default** to let Graphviz place devices on its own, as earlier versions did.
- Use **Devices > Connections > Wiring Diagrams** to pick a scope without opening the object first.

You can check out the [Use Cases](app_use_cases.md) section for more examples.
