"""Preview-time filtering and backend admission checks; never cut a Git hunk."""

import re
import hashlib
from pathlib import PurePosixPath

from .concepts import evidence_index, safe_path
from .errors import LearningError

MAX_DIFF_CHARS = 16_000
MAX_DIFF_LINES = 400
LOCK_NAMES = {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "bun.lockb"}
IGNORED_DIRS = {"dist", "build", "node_modules", ".next", "coverage", "__pycache__"}


def ignored_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    name = parts[-1].lower() if parts else ""
    return (bool(set(part.lower() for part in parts[:-1]) & IGNORED_DIRS)
            or name in LOCK_NAMES or name.endswith((".lock", ".min.js", ".min.css", ".map")))


def file_blocks(raw_diff: str) -> list[tuple[tuple[str, str], str]]:
    """Return complete unquoted Git blocks, including old paths for renames."""
    if not isinstance(raw_diff, str) or not raw_diff.startswith("diff --git "):
        raise LearningError("INVALID_INPUT", "Tam Git diff başlığı gerekli.")
    starts = [match.start() for match in re.finditer(r"^diff --git ", raw_diff, re.MULTILINE)]
    blocks = []
    for start, end in zip(starts, starts[1:] + [len(raw_diff)]):
        block = raw_diff[start:end]
        header = block.split("\n", 1)[0]
        match = re.fullmatch(r"diff --git a/(.+) b/(.+)", header)
        if not match or any(not safe_path(path) or '"' in path for path in match.groups()):
            raise LearningError("INVALID_INPUT", "Desteklenmeyen Git dosya yolu.")
        paths = match.groups()
        # Only examine metadata before the first hunk; deleted source text can
        # itself look like a --- header after Git adds its '-' prefix.
        metadata = block.split("\n@@", 1)[0]
        for prefix, expected in (("--- a/", paths[0]), ("+++ b/", paths[1])):
            found = re.findall(r"^" + re.escape(prefix) + r"([^\n]*)", metadata, re.MULTILINE)
            if any(value.split("\t", 1)[0] != expected for value in found):
                raise LearningError("INVALID_INPUT", "Diff başlık yolları eşleşmiyor.")
        blocks.append((paths, block))
    return blocks


def check_diff_limits(diff: str, *, max_chars: int = MAX_DIFF_CHARS, max_lines: int = MAX_DIFF_LINES) -> None:
    if any(type(value) is not int or value < 1 for value in (max_chars, max_lines)):
        raise ValueError("Diff limits must be positive integers")
    line_count = diff.count("\n") + int(bool(diff) and not diff.endswith("\n"))
    if len(diff) > max_chars or line_count > max_lines:
        raise LearningError("PAYLOAD_TOO_LARGE", "Diff çok büyük. Lütfen daha küçük bir dosya veya staged/unstaged parçası seçin.")


def prune_git_diff(raw_diff: str) -> tuple[str, bool]:
    """Use BEFORE preview/consent/hash. Filter whole files; reject oversized remainder.

    The boolean means files were removed, never that a partial hunk was retained.
    The caller must remove matching context and hash the exact resulting diff.
    This helper does not send, execute, or approve anything.
    """
    selected = [block for paths, block in file_blocks(raw_diff) if not any(ignored_path(path) for path in paths)]
    diff = "".join(selected)
    if not diff.strip():
        raise LearningError("INSUFFICIENT_EVIDENCE", "Filtre sonrası analiz edilebilir dosya kalmadı.")
    check_diff_limits(diff)
    evidence_index({"diff": diff, "context": [], "snapshot_id": hashlib.sha256(diff.encode("utf-8")).hexdigest()})
    return diff, diff != raw_diff


def validate_scope(request: dict, *, max_chars: int, max_lines: int) -> None:
    """Backend defense: reject excluded files, rather than mutate approved data."""
    check_diff_limits(request["diff"], max_chars=max_chars, max_lines=max_lines)
    paths = [path for pair, _ in file_blocks(request["diff"]) for path in pair]
    paths.extend(item["path"] for item in request["context"])
    if any(ignored_path(path) for path in paths):
        raise LearningError("INVALID_INPUT", "Lock, build veya generated dosyaları çıkarıp önizlemeyi yeniden onaylayın.")
