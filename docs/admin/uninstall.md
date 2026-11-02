# Uninstall the App from Nautobot

Here you will find any steps necessary to cleanly remove the App from your Nautobot environment.

## Database Cleanup

None needed. The app adds no models, custom fields, relationships, or jobs, so there is nothing in the database to remove.

## Remove App configuration

Remove `"nautobot_wiring_diagrams"` from `PLUGINS` and its entry from `PLUGINS_CONFIG` in `nautobot_config.py`, then restart Nautobot.

## Uninstall the package

```bash
pip3 uninstall nautobot-wiring-diagrams
```

Remove the requirement from `local_requirements.txt` too, if you added it. Graphviz can be uninstalled if nothing else uses it.
