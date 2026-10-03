"""Validate snapshot identity and index observable new-side diff evidence."""

import hashlib
from pathlib import PurePosixPath
import re

from ..errors import LearningError

HUNK = re.compile(r"^@@ -(\d{1,10})(?:,(\d{1,10}))? \+(\d{1,10})(?:,(\d{1,10}))? @@(?:.*)$")


def safe_path(path: str) -> bool:
    return bool(path and not PurePosixPath(path).is_absolute()
                and ".." not in path.split("/") and "\\" not in path
                and not any(ord(char) < 32 for char in path)
                and not re.match(r"^[A-Za-z]:", path))


def evidence_index(request: dict) -> dict[str, dict[int, str]]:
    """Only new-side hunk lines are citable in v1 (which has no old/new side field).

    Context entries are full files starting at line 1. If supplied, their hunk
    lines must match. Diff-only requests can cite lines present in the diff.
    """
    if hashlib.sha256(request["diff"].encode("utf-8")).hexdigest() != request["snapshot_id"]:
        raise LearningError("STALE_SNAPSHOT", "Diff ile snapshot özeti eşleşmiyor.")
    contexts = {}
    for item in request["context"]:
        path = item["path"]
        if not safe_path(path) or path in contexts:
            raise LearningError("INVALID_INPUT", "Bağlam yolları geçersiz veya yineleniyor.")
        contexts[path] = item["content"].split("\n")

    index: dict[str, dict[int, str]] = {}
    path = None
    old_left = new_left = 0
    line_number = 0
    in_hunk = False
    diff_lines = request["diff"].split("\n")
    if diff_lines[-1] == "":
        diff_lines.pop()
    for line in diff_lines:
        if in_hunk and (old_left or new_left):
            if line.startswith("\\ No newline at end of file"):
                continue
            prefix = line[:1]
            if prefix not in (" ", "+", "-"):
                raise LearningError("INVALID_INPUT", "Diff satır sayıları tutarsız.")
            if prefix in (" ", "-"):
                old_left -= 1
            if prefix in (" ", "+"):
                new_left -= 1
                if path is None or line_number < 1 or line_number in index[path]:
                    raise LearningError("INVALID_INPUT", "Diff kanıt satırı geçersiz.")
                content = line[1:]
                if path in contexts:
                    lines = contexts[path]
                    if line_number > len(lines) or lines[line_number - 1] != content:
                        raise LearningError("STALE_SNAPSHOT", "Bağlam ve diff aynı görüntüye ait değil.")
                index[path][line_number] = content
                line_number += 1
            if old_left < 0 or new_left < 0:
                raise LearningError("INVALID_INPUT", "Diff satır sayıları tutarsız.")
            continue
        if line.startswith("diff --git "):
            path = None
            in_hunk = False
        elif line.startswith("+++ "):
            raw = line[4:].split("\t", 1)[0]
            if raw == "/dev/null":
                path = None
            elif raw.startswith("b/") and safe_path(raw[2:]):
                path = raw[2:]
                if path in index:
                    raise LearningError("INVALID_INPUT", "Diff dosyası yineleniyor.")
                index[path] = {}
            else:
                raise LearningError("INVALID_INPUT", "Desteklenmeyen diff yolu.")
        elif line.startswith("@@"):
            match = HUNK.fullmatch(line)
            if not match:
                raise LearningError("INVALID_INPUT", "Desteklenmeyen diff başlığı.")
            old_start, old_count, new_start, new_count = match.groups()
            old_left = int(old_count) if old_count is not None else 1
            new_left = int(new_count) if new_count is not None else 1
            line_number = int(new_start)
            in_hunk = True
        elif line.startswith(("+", "-", " ")) and in_hunk:
            raise LearningError("INVALID_INPUT", "Diff beklenmeyen ek satır içeriyor.")
    if old_left or new_left:
        raise LearningError("INVALID_INPUT", "Diff kesilmiş; tam hunk gerekli.")
    if not any(index.values()):
        raise LearningError("INSUFFICIENT_EVIDENCE", "Yeni tarafta soruya bağlanabilecek kod satırı yok.")
    if len(index) > 20 or len(contexts) > 20:
        raise LearningError("PAYLOAD_TOO_LARGE", "Bir analiz en fazla 20 dosya içerebilir.")
    return index


def concepts_from_questions(questions: list[dict]) -> list[str]:
    concepts = list(dict.fromkeys(question["concept"].strip() for question in questions))
    if not 2 <= len(concepts) <= 5 or not all(concepts):
        raise LearningError("INVALID_MODEL_OUTPUT", "Çıktı 2–5 farklı kavram içermeli.", True)
    return concepts
