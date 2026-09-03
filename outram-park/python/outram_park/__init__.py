"""outram-park: the outram-park-backend simulation API, in Python.

One submodule per backend crate -- see `backends()` for the list
compiled into this build. Physical quantities are plain `float`s in
SI base units (kelvin, pascal, metre, second, watt, kilogram).
"""

from .outram_park import *  # noqa: F401,F403
from .outram_park import backends, version  # noqa: F401

__all__ = ["backends", "version"] + list(backends())
