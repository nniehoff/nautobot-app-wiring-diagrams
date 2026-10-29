# Nautobot Wiring Diagrams

<!--
Developer Note - Remove Me!

The README will have certain links/images broken until the PR is merged into `develop`. Update the GitHub links with whichever branch you're using (main etc.) if different.

The logo of the project is a placeholder (docs/images/icon-nautobot-wiring-diagrams.png) - please replace it with your app icon, making sure it's at least 200x200px and has a transparent background!

To avoid extra work and temporary links, make sure that publishing docs (or merging a PR) is done at the same time as setting up the docs site on RTD, then test everything.
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/nniehoff/nautobot-app-wiring-diagrams/develop/docs/images/icon-nautobot-wiring-diagrams.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/nniehoff/nautobot-app-wiring-diagrams/actions"><img src="https://github.com/nniehoff/nautobot-app-wiring-diagrams/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://docs.nautobot.com/projects/wiring-diagrams/en/latest/"><img src="https://readthedocs.org/projects/nautobot-app-wiring-diagrams/badge/"></a>
  <a href="https://pypi.org/project/nautobot-wiring-diagrams/"><img src="https://img.shields.io/pypi/v/nautobot-wiring-diagrams"></a>
  <a href="https://pypi.org/project/nautobot-wiring-diagrams/"><img src="https://img.shields.io/pypi/dm/nautobot-wiring-diagrams"></a>
  <br>
  An <a href="https://networktocode.com/nautobot-apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

Nautobot Wiring Diagrams draws port-level wiring diagrams from the cables recorded in Nautobot. Choose a Location (including its child Locations), a Rack, or a Device to see each cabled port and the device, circuit, or power panel on the other end of each cable.

Devices are laid out in columns, busiest in the middle, with redundant switch pairs split either side of the devices cabled to both, so most cables run a short, level way. Diagrams can be filtered by cable type, cable status, and connection kind (data, console, power). Cables are colored from their own color, a per-type color map set in the app config, or the switch they land on. Patch panels can be drawn hop by hop or collapsed into end-to-end connections. In Nautobot the diagram pans, zooms, and highlights a cable end to end on hover, with a cable schedule table below it. Every diagram downloads as PDF, SVG, PNG, or Graphviz DOT, and the schedule as CSV.

Diagrams are rendered with [Graphviz](https://graphviz.org/), which must be installed on the Nautobot server.

## Documentation

Full documentation for this App can be found over on the [Nautobot Docs](https://docs.nautobot.com) website:

- [User Guide](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/user/app_overview/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/nniehoff/nautobot-app-wiring-diagrams/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://docs.nautobot.com/projects/wiring-diagrams/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
