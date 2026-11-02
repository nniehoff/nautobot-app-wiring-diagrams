"""Nautobot development configuration file."""

import os
import sys

from nautobot.core.settings import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from nautobot.core.settings_funcs import is_truthy

#
# Debug
#

DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", "false"))
_TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if DEBUG and not _TESTING:
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: True}

    if "debug_toolbar" not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

#
# Misc. settings
#

ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "")

#
# Database
#

nautobot_db_engine = os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.postgresql")
default_db_settings = {
    "django.db.backends.postgresql": {
        "NAUTOBOT_DB_PORT": "5432",
    },
    "django.db.backends.mysql": {
        "NAUTOBOT_DB_PORT": "3306",
    },
}
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),  # Database username
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),  # Database password
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),  # Database server
        "PORT": os.getenv(
            "NAUTOBOT_DB_PORT", default_db_settings[nautobot_db_engine]["NAUTOBOT_DB_PORT"]
        ),  # Database port, default to postgres
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", "300")),  # Database timeout
        "ENGINE": nautobot_db_engine,
    }
}

# Ensure proper Unicode handling for MySQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}

#
# Redis
#

# The django-redis cache is used to establish concurrent locks using Redis.
# Inherited from nautobot.core.settings
# CACHES = {....}

#
# Celery settings are not defined here because they can be overloaded with
# environment variables. By default they use `CACHES["default"]["LOCATION"]`.
#

#
# Logging
#

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not _TESTING:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "normal": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s : %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() : %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "normal_console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "normal",
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
        },
    }

#
# Apps
#

# Enable installed Apps. Add the name of each App to the list.
PLUGINS = ["nautobot_wiring_diagrams"]

# Apps configuration settings. These settings are used by various Apps that the user may have installed.
# Each key in the dictionary is the name of an installed App and its value is a dictionary of settings.
# Every setting nautobot_wiring_diagrams reads, at its default. Omitted keys fall back to the same defaults
# (default_settings in nautobot_wiring_diagrams/__init__.py).
PLUGINS_CONFIG = {
    "nautobot_wiring_diagrams": {
        # Line color per cable type, keyed by Nautobot's CableTypeChoices value. A leading "#" is optional.
        # Used when "Color by" is "Cable type", and by "Cable color" for cables with no color of their own.
        # Types not listed here draw in default_cable_color. Every key Nautobot 3.2 accepts:
        "cable_type_colors": {
            # "aoc": "#17becf",
            # "cat3": "#bcbd22",
            # "cat5": "#bcbd22",
            # "cat5e": "#1f77b4",
            # "cat6": "#1f77b4",
            # "cat6a": "#1f77b4",
            # "cat7": "#1f77b4",
            # "cat7a": "#1f77b4",
            # "cat8": "#1f77b4",
            # "coaxial": "#8c564b",
            # "dac-active": "#9467bd",
            # "dac-passive": "#9467bd",
            # "mmf": "#ff7f0e",
            # "mmf-om1": "#ff7f0e",
            # "mmf-om2": "#ff7f0e",
            # "mmf-om3": "#2ca02c",
            # "mmf-om4": "#e377c2",
            # "mmf-om5": "#2ca02c",
            # "mrj21-trunk": "#8c564b",
            # "other": "#6c757d",
            # "power": "#000000",
            # "smf": "#ffbf00",
            # "smf-os1": "#ffbf00",
            # "smf-os2": "#ffbf00",
        },
        # Fallback line color. "Color by: Cable type": types missing from cable_type_colors, and their legend
        # row. "Color by: Busier device": devices without a palette color. Under "Cable color" an uncolored,
        # unmapped cable takes the busier device's palette color instead, so this rarely shows there.
        "default_cable_color": "#6c757d",
        # Line style the form starts on: "curved" (Graphviz, server-side) or "square" (ELK, in the browser,
        # with line jumps).
        "default_line_style": "curved",
        # Direction when the form's "Direction" is left blank: "LR" (left to right) or "TB" (top to bottom).
        # Applies to the curved (Graphviz) view and its exports; the square view always runs left to right.
        "default_rankdir": "LR",
        # Largest diagram, in devices and other nodes, the page draws inline. Bigger scopes show a message
        # asking to narrow the filters; exports are not limited.
        "max_nodes": 500,
    }
}
