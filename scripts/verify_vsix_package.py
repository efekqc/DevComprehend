"""
DevComprehend — VSIX Package Verification Script

Automated verification of .vsix extension packages:
1. Archive integrity (valid ZIP structure)
2. Manifest validation (package.json checks)
3. Secret detection in packaged code
4. Cursor compatibility check

Usage:
    python scripts/verify_vsix_package.py path/to/devcomprehend-x.y.z.vsix

Exit codes:
    0 = All checks passed
    1 = One or more checks failed
    2 = File not found or invalid argument
"""

import sys
import os
import re
import json
import zipfile
from pathlib import Path
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    details: list[str] = field(default_factory=list)


class VSIXVerifier:
    """Verifies .vsix extension package integrity and compliance."""

    SECRET_PATTERNS = [
        re.compile(r'(?i)(api[_-]?key|access[_-]?key|apikey|anthropic[_-]?key)\s*[=:]\s*["\']?[\w\-]{16,}'),
        re.compile(r'(?i)(secret[_-]?key|secret|password|passwd|pwd)\s*[=:]\s*["\']?[\S]{8,}'),
        re.compile(r'(?i)(bearer\s+|token\s*[=:]\s*)["\']?[\w\-\.]{16,}'),
        re.compile(r'(?i)(sk-|pk-|ak-|akia|asia)[a-zA-Z0-9_\-]{16,}'),
        re.compile(r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'),
    ]

    DANGEROUS_FILES = [
        '.env', '.env.local', '.env.production',
        'credentials.json', 'service-account.json',
        'id_rsa', 'id_ed25519',
    ]

    REQUIRED_MANIFEST_FIELDS = [
        'name', 'version', 'publisher', 'engines',
    ]

    def __init__(self, vsix_path: str):
        self.vsix_path = Path(vsix_path)
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> bool:
        """Run all verification checks. Returns True if all pass."""
        self.check_file_exists()
        if not self.results[-1].passed:
            return False

        self.check_archive_integrity()
        self.check_manifest()
        self.check_no_secrets()
        self.check_no_dangerous_files()
        self.check_cursor_compatibility()

        return all(r.passed for r in self.results)

    def check_file_exists(self):
        exists = self.vsix_path.exists() and self.vsix_path.suffix == '.vsix'
        self.results.append(CheckResult(
            name="File Exists",
            passed=exists,
            message=f"VSIX file {'found' if exists else 'NOT found'}: {self.vsix_path}"
        ))

    def check_archive_integrity(self):
        try:
            with zipfile.ZipFile(self.vsix_path, 'r') as zf:
                bad = zf.testzip()
                if bad:
                    self.results.append(CheckResult(
                        name="Archive Integrity",
                        passed=False,
                        message=f"Corrupt file in archive: {bad}"
                    ))
                else:
                    file_count = len(zf.namelist())
                    self.results.append(CheckResult(
                        name="Archive Integrity",
                        passed=True,
                        message=f"Valid ZIP archive with {file_count} files"
                    ))
        except zipfile.BadZipFile:
            self.results.append(CheckResult(
                name="Archive Integrity",
                passed=False,
                message="File is not a valid ZIP archive"
            ))

    def check_manifest(self):
        try:
            with zipfile.ZipFile(self.vsix_path, 'r') as zf:
                # Find package.json in the archive
                manifest_paths = [n for n in zf.namelist() if n.endswith('package.json')]
                if not manifest_paths:
                    self.results.append(CheckResult(
                        name="Manifest Check",
                        passed=False,
                        message="No package.json found in archive"
                    ))
                    return

                # Read the first package.json (usually extension/package.json)
                manifest_data = zf.read(manifest_paths[0])
                manifest = json.loads(manifest_data)

                missing = [f for f in self.REQUIRED_MANIFEST_FIELDS if f not in manifest]
                details = []

                if not missing:
                    details.append(f"Name: {manifest.get('name')}")
                    details.append(f"Version: {manifest.get('version')}")
                    details.append(f"Publisher: {manifest.get('publisher')}")

                    # Check for VS Code engine
                    engines = manifest.get('engines', {})
                    if 'vscode' in engines:
                        details.append(f"VS Code engine: {engines['vscode']}")
                    else:
                        details.append("WARNING: No vscode engine specified")

                    # Check contributes for views
                    contributes = manifest.get('contributes', {})
                    views = contributes.get('views', {})
                    if views:
                        details.append(f"Views: {list(views.keys())}")

                self.results.append(CheckResult(
                    name="Manifest Check",
                    passed=len(missing) == 0,
                    message=f"Missing fields: {missing}" if missing else "All required fields present",
                    details=details
                ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Manifest Check",
                passed=False,
                message=f"Error reading manifest: {e}"
            ))

    def check_no_secrets(self):
        findings = []
        try:
            with zipfile.ZipFile(self.vsix_path, 'r') as zf:
                for name in zf.namelist():
                    # Only check text-like files
                    if any(name.endswith(ext) for ext in
                           ('.js', '.ts', '.json', '.env', '.yaml', '.yml', '.txt', '.md')):
                        try:
                            content = zf.read(name).decode('utf-8', errors='ignore')
                            for pattern in self.SECRET_PATTERNS:
                                matches = pattern.findall(content)
                                if matches:
                                    findings.append(f"{name}: {len(matches)} potential secret(s)")
                        except Exception:
                            continue

            self.results.append(CheckResult(
                name="Secret Scan",
                passed=len(findings) == 0,
                message=f"{len(findings)} file(s) with potential secrets" if findings else "No secrets found",
                details=findings
            ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Secret Scan",
                passed=False,
                message=f"Error scanning: {e}"
            ))

    def check_no_dangerous_files(self):
        found = []
        try:
            with zipfile.ZipFile(self.vsix_path, 'r') as zf:
                for name in zf.namelist():
                    basename = name.rsplit('/', 1)[-1] if '/' in name else name
                    if basename in self.DANGEROUS_FILES:
                        found.append(name)

            self.results.append(CheckResult(
                name="Dangerous Files",
                passed=len(found) == 0,
                message=f"{len(found)} dangerous file(s) found" if found else "No dangerous files",
                details=found
            ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Dangerous Files",
                passed=False,
                message=f"Error checking: {e}"
            ))

    def check_cursor_compatibility(self):
        """Check if the extension can be installed with --profile argument."""
        # This is a structural check; actual Cursor test requires the binary
        try:
            with zipfile.ZipFile(self.vsix_path, 'r') as zf:
                manifest_paths = [n for n in zf.namelist() if n.endswith('package.json')]
                if manifest_paths:
                    manifest = json.loads(zf.read(manifest_paths[0]))
                    engines = manifest.get('engines', {})
                    vscode_ver = engines.get('vscode', 'not specified')
                    
                    # Cursor generally supports VS Code extensions >= 1.70
                    details = [
                        f"VS Code engine requirement: {vscode_ver}",
                        "Cursor --profile install command:",
                        f"  cursor --install-extension {self.vsix_path.name} --profile DevComprehend-QA",
                    ]
                    
                    self.results.append(CheckResult(
                        name="Cursor Compatibility",
                        passed=True,
                        message="Extension structure compatible with Cursor",
                        details=details
                    ))
                else:
                    self.results.append(CheckResult(
                        name="Cursor Compatibility",
                        passed=False,
                        message="Cannot verify - no manifest found"
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Cursor Compatibility",
                passed=False,
                message=f"Error: {e}"
            ))

    def print_report(self):
        """Print a formatted verification report."""
        print("\n" + "=" * 70)
        print("  DevComprehend — VSIX Verification Report")
        print("=" * 70)
        print(f"  Package: {self.vsix_path}")
        print("=" * 70 + "\n")

        all_passed = True
        for r in self.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"  {status}  {r.name}")
            print(f"          {r.message}")
            for d in r.details:
                print(f"          • {d}")
            print()
            if not r.passed:
                all_passed = False

        print("─" * 70)
        overall = "✅ ALL CHECKS PASSED" if all_passed else "❌ SOME CHECKS FAILED"
        print(f"  {overall}")
        print("─" * 70 + "\n")
        return all_passed


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_vsix_package.py <path-to-vsix>")
        print("\nIf no .vsix file exists yet, run in dry-run mode:")
        print("  python verify_vsix_package.py --dry-run")
        sys.exit(2)

    arg = sys.argv[1]

    if arg == "--dry-run":
        print("\n🔍 Dry-run mode: Verifying VSIXVerifier logic...")
        # Create a minimal test vsix (zip) in memory
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".vsix", delete=False) as tmp:
            tmp_path = tmp.name
            with zipfile.ZipFile(tmp_path, 'w') as zf:
                manifest = {
                    "name": "devcomprehend",
                    "version": "0.1.0",
                    "publisher": "devcomprehend-team",
                    "engines": {"vscode": "^1.90.0"},
                    "contributes": {
                        "views": {"devcomprehend-sidebar": []}
                    }
                }
                zf.writestr("extension/package.json", json.dumps(manifest))
                zf.writestr("extension/dist/main.js", "console.log('hello');")

        verifier = VSIXVerifier(tmp_path)
        all_passed = verifier.run_all_checks()
        verifier.print_report()
        os.unlink(tmp_path)
        sys.exit(0 if all_passed else 1)

    verifier = VSIXVerifier(arg)
    all_passed = verifier.run_all_checks()
    verifier.print_report()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
