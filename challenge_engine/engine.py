#!/usr/bin/env python3
"""Compatibility import for the current hardened Challenge Engine implementation."""
try:
    from .engine_v6 import *  # noqa: F401,F403
except ImportError:
    from engine_v6 import *  # noqa: F401,F403
