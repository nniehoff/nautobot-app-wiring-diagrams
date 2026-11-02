# Upgrading the App

Here you will find any steps necessary to upgrade the App in your Nautobot environment.

## Upgrade Guide

When a new release comes out it may be necessary to run a migration of the database to account for any changes in the data models used by this app. Execute the command `nautobot-server post_upgrade` within the runtime environment of your Nautobot installation after updating the `nautobot-wiring-diagrams` package via `pip`.

The app has no models today, so `post_upgrade` runs no migrations for it, but it also collects the app's updated static files (the diagram's JavaScript and the bundled ELK layout library), which the diagram page loads. Restart Nautobot afterwards. Check the [release notes](release_notes/index.md) for changed settings or defaults before upgrading.
