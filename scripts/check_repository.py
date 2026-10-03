"""Validate the scaffold and local Markdown file links using stdlib."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md", "CONTRIBUTING.md", "SECURITY.md", "AGENTS.md",
    ".github/CODEOWNERS", ".github/workflows/repository-check.yml",
    "docs/product/mvp.md", "docs/team/ownership.md",
    "docs/architecture/overview.md", "docs/planning/backlog.md",
    "apps/extension/README.md", "services/api/README.md",
    "services/learning/README.md", "contracts/README.md",
)
errors = []
for name in REQUIRED:
    if not (ROOT / name).is_file():
        errors.append(f"Missing: {name}")
for path in ROOT.rglob("*.md"):
    if any(part in {".git", "node_modules", ".venv"} for part in path.parts):
        continue
    body = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
        if "://" in target or target.startswith(("#", "mailto:")):
            continue
        target = target.split("#", 1)[0]
        if target and not (path.parent / target).exists():
            errors.append(f"Broken link in {path.relative_to(ROOT)}: {target}")
if errors:
    raise SystemExit("\n".join(errors))
print("Repository structure and local Markdown links: OK")
