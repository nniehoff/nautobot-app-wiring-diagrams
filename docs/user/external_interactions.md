# External Interactions

This document describes external dependencies and prerequisites for this App to operate, including system requirements, API endpoints, interconnection or integrations to other applications or services, and similar topics.

## External System Integrations

### From the App to Other Systems

The app calls no external services. It needs the [Graphviz](https://graphviz.org/) `dot` command on each Nautobot web server, which it runs as a local process to draw curved diagrams and exports. Square-line diagrams are laid out in the browser by [ELK](https://eclipse.dev/elk/), which ships with the app as a static file; the browser loads nothing from the internet.

### From Other Systems to the App

The app has no REST API of its own. Diagrams can be downloaded from the export endpoint, a regular Nautobot page:

```text
GET /plugins/wiring-diagrams/export/<location|rack|device>/<uuid>/?format=<pdf|svg|png|dot|csv>
```

`format` defaults to `pdf`; `csv` returns the cable schedule instead of the drawing. The endpoint takes the same options as the diagram page:

| Parameter | Values | Default |
| --------- | ------ | ------- |
| `cable_type` | A cable type value, repeatable (`cat6`, `smf`, ...) | all types |
| `status` | A cable status UUID, repeatable | all statuses |
| `kind` | `data`, `console`, `power`, repeatable | `data` and `console` |
| `collapse_patch_panels` | `on` | off |
| `color_by` | `cable`, `type`, `device` | `cable` |
| `rankdir` | `LR`, `TB` | `default_rankdir` |
| `arrange` | `columns`, `free` | `columns` |
| `order` | `cables`, `rack` | `cables` |
| `group_by_rack` | `on` | on, unless `rankdir` is given without it |

Exports always draw curved lines with Graphviz; `line_style` is ignored. The user needs permission to view the scope object, and the diagram only includes the cables and devices that user can view.

The endpoint is a UI view, not part of the REST API, so it needs a logged-in session: Nautobot API tokens (`Authorization: Token ...`) are not accepted and get a redirect to the login page. A script must log in first and send the session cookie. For example:

```text
https://nautobot.example.com/plugins/wiring-diagrams/export/rack/<uuid>/?format=pdf&kind=data&kind=power
```

## Nautobot REST API endpoints

None. The app adds no models, so it adds nothing to the REST or GraphQL APIs.
