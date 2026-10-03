"""
DevComprehend — Push feat/DC-002-contracts-infra to GitHub Remote

Usage:
    python scripts/push_to_remote.py [GITHUB_TOKEN]

If GITHUB_TOKEN is not provided as an argument, it will read from $GITHUB_TOKEN
or prompt securely in the terminal.
"""

import sys
import os
import getpass
from dulwich.repo import Repo
from dulwich import porcelain

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REMOTE_REPO_URL = "https://github.com/Anonymbordo/DevComprehend.git"
BRANCH_REF = "refs/heads/feat/DC-002-contracts-infra"


def push_with_token(token: str, username: str = "git"):
    r = Repo(REPO_PATH)
    # Construct authenticated URL (token in URL without logging it)
    auth_url = f"https://{username}:{token}@github.com/Anonymbordo/DevComprehend.git"
    print(f"Connecting to {REMOTE_REPO_URL}...")
    print(f"Pushing branch '{BRANCH_REF}'...")
    try:
        porcelain.push(r, auth_url, BRANCH_REF)
        print("\n✅ PUSH SUCCESSFUL!")
        print(f"Branch 'feat/DC-002-contracts-infra' successfully pushed to {REMOTE_REPO_URL}")
        print("\nYou can now open a Pull Request at:")
        print("👉 https://github.com/Anonymbordo/DevComprehend/compare/main...feat/DC-002-contracts-infra")
        return True
    except Exception as e:
        print(f"\n❌ Push failed: {e}")
        return False


def main():
    token = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        token = sys.argv[1].strip()
    elif os.environ.get("GITHUB_TOKEN"):
        token = os.environ.get("GITHUB_TOKEN").strip()
    elif os.environ.get("GH_TOKEN"):
        token = os.environ.get("GH_TOKEN").strip()

    if not token:
        print("GitHub Personal Access Token (PAT) required for push.")
        print("You can generate one with 'repo' scope at: https://github.com/settings/tokens")
        try:
            token = getpass.getpass("Enter GitHub Token: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

    if not token:
        print("No token provided. Aborted.")
        sys.exit(1)

    success = push_with_token(token)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
