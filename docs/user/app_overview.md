# App Overview

This document provides an overview of the App including critical information and important considerations when applying it to your Nautobot environment.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description

Nautobot Wiring Diagrams draws a port-level wiring diagram from the cables already recorded in Nautobot. Pick a Location (including its child Locations), a Rack, or a single Device. The diagram shows every cabled port on those devices and the device, circuit, or power panel at the other end of each cable. Diagrams can be viewed in Nautobot and downloaded as PDF, SVG, PNG, or Graphviz DOT source.

Each device is drawn as a box with one row per cabled port, and each cable is a line between two ports. Planned cables are dashed and decommissioning cables are dotted.

Devices are laid out in columns by how many cabled ports they have, so most cables run a short way between neighboring columns:

- The busiest devices (at least two thirds as many cabled ports as the busiest one) sit in the middle, the devices cabled to them one column out, and the devices behind those one further.
- A redundant pair, such as two spine or core switches, is split instead: one on each side, with the devices cabled to both between them. Each of those devices then has one short cable to either side.
- Within a column, devices are ordered by the ports they are cabled to, so cables run as level as possible. Devices that have further devices of their own, such as access switches, go below the rest. Ordering by rack position (top unit first) is available instead.
- Each cable leaves its port from the side facing the device at the other end.

Lines take the cable's own color, then a color per cable type if one is configured, then a color for the busier device at either end, so the cables of one switch share a color. Devices in scope are boxed by Rack when the diagram covers two or more Racks.

Cables are drawn as curves by default. Choose **Line style: Square with line jumps** to draw them as horizontal and vertical runs instead, with a small hop wherever one cable crosses another, as in an electrical schematic. Square lines are laid out in the browser by [ELK](https://eclipse.dev/elk/) rather than by Graphviz, so:

- They always use columns, left to right, and never draw rack boxes.
- Their PDF, SVG, and PNG downloads are made in the browser from what is on screen. The export URL below always returns curved lines.
- They do not need Graphviz on the server.

In Nautobot, the diagram can be panned and zoomed. Hovering a cable highlights it and both of its ends; hovering a port or a device highlights all of its cables.

Below the diagram, the **Cable schedule** lists every cable drawn: both devices and ports, the cable, its type, color, status and length, and whether the line stands for a path through patch panels. It downloads as CSV.

Diagrams can be filtered by:

- Cable type (Cat6, single-mode fiber, power, and so on)
- Cable status
- Connection kind: data (interfaces, front and rear ports, circuit terminations), console, or power. Power is left out by default.

Patch panels are drawn hop by hop by default: front port, rear port, and the trunk cable between panels. Enabling **Collapse patch panels** replaces each run with a single bold line between the two endpoints, using Nautobot's traced cable paths.

## Audience (User Personas) - Who should use this App?

- Data center and lab technicians who need a printable wiring sheet for a rack
- Network engineers checking how a device is patched before a change
- Anyone documenting a site's physical cabling

## Authors and Maintainers

- Nick Niehoff (@nniehoff)

## Nautobot Features Used

- A **Wiring Diagram** tab on Location, Rack, and Device detail pages
- A **Devices > Connections > Wiring Diagrams** page with a Location, Rack, or Device picker
- An export endpoint at `/plugins/wiring-diagrams/export/<location|rack|device>/<uuid>/?format=pdf|svg|png|dot|csv` that takes the same filter parameters as the diagram page

The app adds no models, so it has no database migrations. Users need the `dcim.view_cable` permission, and diagrams only include objects the user is allowed to view.

### Extras

The app creates no custom fields or jobs.
