"""Single point of truth for the version of the athena_client package."""

import importlib.metadata

__version__ = importlib.metadata.version("athena_client")
