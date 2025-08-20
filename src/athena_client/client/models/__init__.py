"""Package containing input models for the Athena client.

This package contains the data models and classes used to structure input data
for the Athena classification system.
"""

from .input_model import ClassificationInput, PreSizedInput

__all__ = ["ClassificationInput", "PreSizedInput"]
