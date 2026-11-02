# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

- The app is compatible with Nautobot 3.2.0 and higher.
- Databases supported: PostgreSQL, MySQL
- [Graphviz](https://graphviz.org/) must be installed on every Nautobot web server, so the `dot` command is on the `PATH`. On Debian or Ubuntu, including images built from `networktocode/nautobot`, run `apt-get install graphviz`.

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Access Requirements

The app reads Nautobot data only and needs no access to external systems.

## Install Guide

!!! note
    Apps can be installed from the [Python Package Index](https://pypi.org/) or locally. See the [Nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/app-install/) for more details. The pip package name for this app is [`nautobot-wiring-diagrams`](https://pypi.org/project/nautobot-wiring-diagrams/).

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-wiring-diagrams
```

To ensure Nautobot Wiring Diagrams is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-wiring-diagrams` package:

```shell
echo nautobot-wiring-diagrams >> local_requirements.txt
```

In a container image built on `networktocode/nautobot`, install Graphviz and the package in the image instead; Nautobot cannot load apps added at runtime.

Once installed, the app needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_wiring_diagrams"` to the `PLUGINS` list.
- Append the `"nautobot_wiring_diagrams"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_wiring_diagrams"]

PLUGINS_CONFIG = {
    "nautobot_wiring_diagrams": {
        "cable_type_colors": {"cat6": "#1f77b4", "smf": "#ffbf00", "power": "#d62728"},
    }
}
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`). The app has no database migrations, but this also collects its static files (the diagram's JavaScript and the bundled ELK layout library) and clears the cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## App Configuration

The app behavior can be controlled with the following list of settings:

| Key | Example | Default | Description |
| --- | ------- | ------- | ----------- |
| `cable_type_colors` | `{"cat6": "#1f77b4"}` | `{}` | Line color per cable type, keyed by Nautobot's cable type value (`cat6`, `smf-os2`, `dac-passive`, `power`, ...). The leading `#` is optional. Used for every cable when **Color by** is **Cable type**, and for cables with no color of their own when it is **Cable color**. |
| `default_cable_color` | `"#333333"` | `"#6c757d"` | Fallback line color: for cable types missing from `cable_type_colors` when coloring by type (and their legend row), and for a device with no palette color when coloring by device. Under **Cable color**, an uncolored, unmapped cable takes the busier device's color instead. |
| `default_line_style` | `"square"` | `"curved"` | Line style the form starts on: `curved` (drawn by Graphviz on the server) or `square` (square lines with jumps, laid out in the browser). |
| `default_rankdir` | `"TB"` | `"LR"` | Direction when the form's **Direction** is blank: `LR` (left to right) or `TB` (top to bottom). Curved diagrams and exports only; square lines always run left to right. |
| `max_nodes` | `1000` | `500` | Diagrams with more nodes than this are not drawn in the page; they can still be exported. |

`development/nautobot_config.py` lists every setting at its default, with every cable type key Nautobot accepts as a commented example.
