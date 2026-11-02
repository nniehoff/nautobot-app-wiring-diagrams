# Using the App

This document describes common use-cases and scenarios for this App.

## General Usage

Open a Location, Rack, or Device and select its **Wiring Diagram** tab, or use **Devices > Connections > Wiring Diagrams** and pick one. A Location covers every device in it and its child Locations. **Options** above the diagram filter and style it; **Update** redraws, and every download uses the same options.

## Use-cases and common workflows

### Print a wiring sheet for a rack

Open the Rack's **Wiring Diagram** tab, leave **Order by** on **Keep cables level** (or choose **Rack position** to match the physical layout), and select **PDF**. The **Cable schedule** below the diagram downloads as **CSV** for a port-by-port checklist.

### Check how a device is patched before a change

Open the Device's tab. The diagram shows only that device's cabled ports and what is at the other end of each cable, including circuits and power panels. Hover a port to highlight its cable end to end.

### Trace connections through patch panels

By default each patch panel hop is drawn: front port, rear port, and the trunk between panels. Turn on **Collapse patch panels** to replace each run with one bold line between the two endpoints, from Nautobot's traced cable paths. The cable schedule marks those rows as paths.

### Audit one kind of cabling

Choose **Cable types** (for example only single-mode fiber) and **Color by: Cable type** for a legend. With `cable_type_colors` set, the same type is the same color on every diagram. **Status** filters to planned or decommissioning cables, which are drawn dashed and dotted.

### Link to a diagram

The export endpoint returns any diagram as a file with its options in the URL, so a link can be shared or bookmarked. It needs a logged-in Nautobot session, not an API token. See [External Interactions](external_interactions.md).
