#!/usr/bin/env bash
# =============================================================================
# DevComprehend — VSIX & Cursor Installation Verification Script
# =============================================================================
# Usage: ./scripts/verify_vsix_and_cursor.sh <path-to-vsix>
#
# This script:
#   1. Verifies the VSIX archive integrity
#   2. Checks the manifest for required fields
#   3. Scans for leaked secrets in packaged code
#   4. Tests VS Code installation
#   5. Tests Cursor installation with --profile
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass_count=0
fail_count=0

check_pass() {
    echo -e "  ${GREEN}✅ PASS${NC}  $1"
    ((pass_count++))
}

check_fail() {
    echo -e "  ${RED}❌ FAIL${NC}  $1"
    ((fail_count++))
}

check_warn() {
    echo -e "  ${YELLOW}⚠️  WARN${NC}  $1"
}

# ─── Argument Check ───────────────────────────────────────────────
if [ $# -lt 1 ]; then
    echo "Usage: $0 <path-to-vsix>"
    echo "       $0 --dry-run    (test without a real .vsix file)"
    exit 2
fi

VSIX_PATH="$1"

echo ""
echo "======================================================================"
echo "  DevComprehend — VSIX & Cursor Verification"
echo "======================================================================"

# ─── Dry Run Mode ─────────────────────────────────────────────────
if [ "$VSIX_PATH" = "--dry-run" ]; then
    echo "  Mode: Dry run (using Python verifier)"
    echo "======================================================================"
    python scripts/verify_vsix_package.py --dry-run
    exit $?
fi

echo "  Package: $VSIX_PATH"
echo "======================================================================"
echo ""

# ─── Check 1: File exists ─────────────────────────────────────────
if [ -f "$VSIX_PATH" ]; then
    check_pass "VSIX file exists"
else
    check_fail "VSIX file not found: $VSIX_PATH"
    echo ""
    echo "──────────────────────────────────────────────────────────────────────"
    echo "  ❌ VERIFICATION ABORTED — File not found"
    echo "──────────────────────────────────────────────────────────────────────"
    exit 1
fi

# ─── Check 2: Archive integrity ───────────────────────────────────
if unzip -tq "$VSIX_PATH" > /dev/null 2>&1; then
    FILE_COUNT=$(unzip -l "$VSIX_PATH" | tail -1 | awk '{print $2}')
    check_pass "Valid ZIP archive ($FILE_COUNT files)"
else
    check_fail "Invalid ZIP archive"
fi

# ─── Check 3: package.json manifest ──────────────────────────────
MANIFEST=$(unzip -p "$VSIX_PATH" '*/package.json' 2>/dev/null | head -c 10000)
if [ -n "$MANIFEST" ]; then
    check_pass "package.json found in archive"
    
    # Check required fields
    for field in name version publisher engines; do
        if echo "$MANIFEST" | python -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null; then
            check_pass "Manifest has '$field' field"
        else
            check_fail "Manifest missing '$field' field"
        fi
    done
else
    check_fail "No package.json found in archive"
fi

# ─── Check 4: Secret scan ────────────────────────────────────────
SECRET_HITS=$(unzip -p "$VSIX_PATH" '*.js' '*.ts' '*.json' '*.env' 2>/dev/null | \
    grep -ciE '(api[_-]?key|secret|password|passwd)\s*[=:]\s*["'\''"]{0,1}[a-zA-Z0-9_\-]{16,}|sk-[a-zA-Z0-9]{20,}|-----BEGIN .* PRIVATE KEY-----' || true)

if [ "$SECRET_HITS" -eq 0 ] 2>/dev/null; then
    check_pass "No secrets detected in packaged code"
else
    check_fail "Potential secrets found ($SECRET_HITS matches)"
fi

# ─── Check 5: No .env or credential files ────────────────────────
DANGEROUS=$(unzip -l "$VSIX_PATH" 2>/dev/null | grep -cE '\.(env|env\.local|env\.production)$|credentials\.json|service-account|id_rsa|id_ed25519' || true)
if [ "$DANGEROUS" -eq 0 ] 2>/dev/null; then
    check_pass "No dangerous files (.env, credentials, keys) in archive"
else
    check_fail "Dangerous files found in archive ($DANGEROUS matches)"
fi

# ─── Check 6: VS Code installation test ──────────────────────────
if command -v code &> /dev/null; then
    PROFILE="DC-QA-$(date +%s)"
    if code --profile "$PROFILE" --install-extension "$VSIX_PATH" 2>/dev/null; then
        check_pass "VS Code installation successful (profile: $PROFILE)"
        code --profile "$PROFILE" --uninstall-extension devcomprehend 2>/dev/null || true
    else
        check_fail "VS Code installation failed"
    fi
else
    check_warn "VS Code CLI not found — skipping installation test"
fi

# ─── Check 7: Cursor installation test ───────────────────────────
if command -v cursor &> /dev/null; then
    CURSOR_PROFILE="DC-QA-Cursor-$(date +%s)"
    if cursor --profile "$CURSOR_PROFILE" --install-extension "$VSIX_PATH" 2>/dev/null; then
        check_pass "Cursor installation successful (profile: $CURSOR_PROFILE)"
        cursor --profile "$CURSOR_PROFILE" --uninstall-extension devcomprehend 2>/dev/null || true
    else
        check_fail "Cursor installation failed"
    fi
else
    check_warn "Cursor CLI not found — skipping installation test"
fi

# ─── Summary ──────────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────────────────────────────"
if [ "$fail_count" -eq 0 ]; then
    echo -e "  ${GREEN}✅ ALL $pass_count CHECKS PASSED${NC}"
else
    echo -e "  ${RED}❌ $fail_count FAILED${NC}, ${GREEN}$pass_count PASSED${NC}"
fi
echo "──────────────────────────────────────────────────────────────────────"
echo ""

[ "$fail_count" -eq 0 ]
