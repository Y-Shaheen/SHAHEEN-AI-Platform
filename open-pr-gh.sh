#!/usr/bin/env bash
set -euo pipefail

# open-pr-gh.sh
# Create a GitHub PR for the current branch using GitHub CLI (gh).

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI 'gh' is not installed or not on PATH."
  echo "Install from https://cli.github.com/ and authenticate with 'gh auth login'."
  exit 1
fi

HEAD_BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ -n "$HEAD_BRANCH" ] || { echo "ERROR: Could not determine current branch."; exit 1; }

REMOTE_DEFAULT=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p' || true)
if [ -z "$REMOTE_DEFAULT" ]; then
  if git ls-remote --heads origin main >/dev/null 2>&1; then
    REMOTE_DEFAULT="main"
  elif git ls-remote --heads origin master >/dev/null 2>&1; then
    REMOTE_DEFAULT="master"
  else
    REMOTE_DEFAULT="main"
  fi
fi

PR_TITLE="feat(i18n): add Arabic (ar) translations and RTL support"

PR_BODY=$(cat <<'EOF'
This PR adds complete Arabic (ar) localization support for the dashboard and RTL layout handling.

Summary of changes:
- Add Arabic locale files under `dashboard/src/i18n/locales/ar/`.
- Register Arabic locale and RTL support.
- Update translations and styles.
- Validate UI in RTL mode.

Testing:
1. cd dashboard
2. pnpm install || npm install
3. pnpm dev
4. Switch language to العربية and verify RTL.

Notes:
- No secrets added.
- REVIEWERS, ASSIGNEE, LABELS and DRAFT env vars are supported.
EOF
)

GH_CMD=("gh" "pr" "create" "--title" "$PR_TITLE" "--body" "$PR_BODY" "--base" "$REMOTE_DEFAULT" "--head" "$HEAD_BRANCH")

if [ "${DRAFT:-0}" = "1" ] || [ "${DRAFT:-0}" = "true" ]; then
  GH_CMD+=("--draft")
fi

if [ -n "${LABELS:-}" ]; then
  IFS=',' read -ra LABS <<< "$LABELS"
  for lab in "${LABS[@]}"; do
    lab_trimmed="$(echo "$lab" | xargs)"
    [ -n "$lab_trimmed" ] && GH_CMD+=("--label" "$lab_trimmed")
  done
else
  GH_CMD+=("--label" "i18n" "--label" "feature")
fi

[ -n "${ASSIGNEE:-}" ] && GH_CMD+=("--assignee" "$ASSIGNEE")

if [ -n "${REVIEWERS:-}" ]; then
  IFS=',' read -ra RV <<< "$REVIEWERS"
  for r in "${RV[@]}"; do
    r_trimmed="$(echo "$r" | xargs)"
    [ -n "$r_trimmed" ] && GH_CMD+=("--reviewer" "$r_trimmed")
  done
fi

echo "Creating PR on GitHub..."
echo "Command: ${GH_CMD[*]}"

set -x
"${GH_CMD[@]}"
set +x

echo "PR creation attempted. If successful, run: gh pr view --web"
