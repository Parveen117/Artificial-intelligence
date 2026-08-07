#!/usr/bin/env python3
"""Compatibility import for the hardened Challenge Engine implementation."""
try:
    from .engine_v2 import *  # noqa: F401,F403
except ImportError:
    from engine_v2 import *  # noqa: F401,F403
