"""Backend-only learning adapter. No Git, authentication or persistence side effects."""

from .engine import LearningEngine
from .errors import LearningError

__all__ = ["LearningEngine", "LearningError"]
