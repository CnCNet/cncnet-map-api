"""
Any constants that need to be used in any ``kirovy.settings.*`` file, or before django initializes.

This is necessary to avoid circular dependency issues. The regular ``constants`` directory
imports ``django.conf.settings``, so we can't import from ``constants`` until after django has
finished initializing.
"""

import enum


class RunEnvironment(str, enum.Enum):
    PRODUCTION = "prod"
    CI = "ci"
    DEVELOPMENT = "dev"
