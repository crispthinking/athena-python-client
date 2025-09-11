"""Single point of truth for the version of the package."""

import importlib.metadata

__version__ = importlib.metadata.version("resolver-athena-client")
