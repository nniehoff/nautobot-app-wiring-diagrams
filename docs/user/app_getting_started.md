# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md). Graphviz must be installed on the Nautobot server.

## First steps with the App

1. Open a Rack that has cabled devices in it.
2. Select the **Wiring Diagram** tab. The diagram shows each device in the rack with its cabled ports, and the far end of each cable.
3. Under **Options**, choose one or more **Cable types**, for example only Cat6, and select **Update**.
4. Select **PDF** above the diagram to download it with the same options.

The same tab is available on Locations (covering every device in the Location and its child Locations) and on Devices.

## What are the next steps?

- Set `cable_type_colors` in `PLUGINS_CONFIG` so each cable type has a consistent color. Then choose **Color by: Cable type** to add a legend to the diagram.
- Try **Collapse patch panels** to see end-to-end connections through your patch panels.
- Use **Devices > Connections > Wiring Diagrams** to pick a scope without opening the object first.

You can check out the [Use Cases](app_use_cases.md) section for more examples.
