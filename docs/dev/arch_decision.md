# Architecture Decision Records

The intention is to document deviations from a standard Model View Controller (MVC) design.

## No models

Diagrams are computed on every request from Nautobot's own Cable, Device, and port models. The app stores nothing, so it has no migrations, REST API, or GraphQL types, and a diagram is never out of date.

## Graphviz on the server, ELK in the browser

Curved diagrams and every export are rendered by the Graphviz `dot` command on the server, which gives the same output for the page, PDF, SVG, PNG, and DOT. Graphviz cannot draw orthogonal lines with line jumps, so the **Square with line jumps** style is laid out in the browser by [ELK](https://eclipse.dev/elk/) (bundled as a static file, no CDN) from the data `to_layout` returns. Its downloads are made in the browser from what is on screen.

## Column layout before Graphviz

Graphviz's own placement puts the busiest switches wherever its ranking lands them, so cables cross the page. `assign_columns` in `graph.py` places devices in columns first (busiest in the middle, redundant pairs split either side) and orders each column to keep cables level; Graphviz and ELK only route the lines. **Arrange: Graphviz default** turns this off.
