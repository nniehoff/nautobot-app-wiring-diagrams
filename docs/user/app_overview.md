# App Overview

This document provides an overview of the App including critical information and important considerations when applying it to your Nautobot environment.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description

Nautobot Wiring Diagrams draws a port-level wiring diagram from the cables already recorded in Nautobot. Pick a Location (including its child Locations), a Rack, or a single Device. The diagram shows every cabled port on those devices and the device, circuit, or power panel at the other end of each cable. Diagrams can be viewed in Nautobot and downloaded as PDF, SVG, PNG, or Graphviz DOT source.

Each device is drawn as a box with one row per cabled port, and each cable is a line between two ports. Lines are colored from the cable's own color, falling back to a color per cable type. Planned cables are dashed and decommissioning cables are dotted. Devices in scope are grouped by Rack.

Diagrams can be filtered by:

- Cable type (Cat6, single-mode fiber, power, and so on)
- Cable status
- Connection kind: data (interfaces, front and rear ports, circuit terminations), console, or power

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
- An export endpoint at `/plugins/wiring-diagrams/export/<location|rack|device>/<uuid>/?format=pdf|svg|png|dot` that takes the same filter parameters as the diagram page

The app adds no models, so it has no database migrations. Users need the `dcim.view_cable` permission, and diagrams only include objects the user is allowed to view.

### Extras

The app creates no custom fields or jobs.
