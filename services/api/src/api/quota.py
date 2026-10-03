"""Pilot quota policy: per-user daily limits from the pilot protocol."""

from dataclasses import dataclass

from .errors import ApiError


@dataclass(frozen=True)
class QuotaPolicy:
    analyses_per_day: int = 5
    evaluations_per_day: int = 20

    def __post_init__(self):
        if any(type(value) is not int or value < 1
               for value in (self.analyses_per_day, self.evaluations_per_day)):
            raise ValueError("Quota limits must be positive integers")

    def limit(self, kind: str) -> int:
        return {"analysis": self.analyses_per_day,
                "evaluation": self.evaluations_per_day}[kind]

    def reserve(self, store, user_id: str, kind: str) -> None:
        """Atomically consume one unit; raises 429 when the daily limit is hit."""
        with store._lock:
            count = store.usage(user_id, kind)
            if count >= self.limit(kind):
                raise ApiError(429, "QUOTA_EXCEEDED", "Günlük pilot kotası doldu.", True)
            store.increment_usage(user_id, kind)
