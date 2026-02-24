"""Metadata command mixin composition."""

from .meta_generation import MetadataGenerationCommandsMixin
from .meta_inspection import MetadataInspectionCommandsMixin


class MetadataCommandsMixin(
    MetadataGenerationCommandsMixin,
    MetadataInspectionCommandsMixin,
):
    """Compose metadata command families into one command mixin."""

    pass
