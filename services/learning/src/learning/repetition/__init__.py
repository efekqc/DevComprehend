"""A transparent pilot policy, not a validated model of long-term mastery."""

from datetime import datetime, timedelta, timezone

POLICY_VERSION = "repetition-2"


def plan(results: list[dict], uncertain: bool, now: datetime) -> tuple[str, str | None]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A timezone-aware clock is required")
    if uncertain:
        due = (now.astimezone(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        return "unassessed", due
    if not results:
        return "unassessed", None
    statuses = {item["result"] for item in results}
    demonstrated = statuses == {"met"}
    days = 7 if demonstrated else (1 if "missing" in statuses else 3)
    due = (now.astimezone(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
    return "demonstrated" if demonstrated else "developing", due
