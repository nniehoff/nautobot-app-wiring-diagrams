# Extending the App

Extending the application is welcome, however it is best to open an issue first, to ensure that a PR would be accepted and makes sense in terms of features and design.

The app is split so each part can change on its own:

- `graph.py` builds a `WiringGraph` (nodes, ports, edges) from Nautobot cables for a scope and `DiagramOptions`, and assigns layout columns. It knows nothing about drawing.
- `render.py` turns a `WiringGraph` into Graphviz DOT (`to_dot`), or into layout data for the browser's square-line view (`to_layout`), and holds the coloring rules.
- `forms.py` maps the query string to `DiagramOptions` and render arguments; `views.py` and `template_content.py` add the page, the tabs, and the export endpoint.

A new export format is an entry in `EXPORT_FORMATS` in `render.py` that Graphviz can render. A new filter is a field on `WiringDiagramOptionsForm` and a matching field on `DiagramOptions` that `build_graph` applies.
