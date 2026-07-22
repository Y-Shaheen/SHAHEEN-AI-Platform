#!/usr/bin/env bash
set -euo pipefail

# open-pr-gh.sh
# Create a GitHub PR for the current branch using GitHub CLI (gh).
# Usage: ./open-pr-gh.sh
# Optional env:
#   REVIEWERS="alice,bob"    -> add as reviewers
#   ASSIGNEE="alice"         -> add assignee
#   DRAFT=1                  -> create draft PR
#   LABELS="i18n,feature"    -> comma-separated labels to add

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository."
  exit 1
fi

# Ensure gh is installed
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI 'gh' is not installed or not on PATH."
  echo "Install from https://cli.github.com/ and authenticate with 'gh auth login'."
  exit 1
fi

# Determine current branch
HEAD_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ -z "$HEAD_BRANCH" ]; then
  echo "ERROR: Could not determine current branch."
  exit 1
fi

# Determine remote default branch (origin HEAD)
REMOTE_DEFAULT=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p' || true)
if [ -z "$REMOTE_DEFAULT" ]; then
  # fallback: check if main or master exists on remote
  if git ls-remote --heads origin main >/dev/null 2>&1; then
    REMOTE_DEFAULT="main"
  elif git ls-remote --heads origin master >/dev/null 2>&1; then
    REMOTE_DEFAULT="master"
  else
    REMOTE_DEFAULT="main"
  fi
fi

# PR metadata
PR_TITLE="feat(i18n): add Arabic (ar) translations and RTL support"
read -r -d '' PR_BODY <<'EOF'
This PR adds complete Arabic (ar) localization support for the dashboard and RTL layout handling.

Summary of changes:
- Add Arabic locale files under `dashboard/src/i18n/locales/ar/`:
  - core: common.json, actions.json, status.json, navigation.json, header.json, shared.json
  - features: dashboard.json, chat.json, settings.json
  - messages: errors.json, success.json, validation.json
- Update `dashboard/src/i18n/composables.ts`:
  - Register 'ar' in available locales
  - Add Arabic option ("العربية") to languageOptions
  - Persist locale to localStorage
  - Toggle `document.documentElement.lang` and `dir` and a `body.is-rtl` class when Arabic is selected
- Update `dashboard/src/scss/style.scss`:
  - Append RTL helper rules to handle direction, flipping, and spacing for RTL layouts
- Update `dashboard/src/i18n/translations.ts`:
  - (Imports + mapping) Register Arabic translation imports and an 'ar' mapping entry so it is bundled at build time

Testing & validation:
1. Checkout this branch locally (it should already be the current branch).
2. Start the dashboard dev server:
   cd dashboard
   pnpm install   # or npm install
   pnpm dev
3. Open the UI and switch language to "العربية" in the language selector.
4. Verify:
   - The html element has lang="ar" and dir="rtl"
   - document.body.classList contains "is-rtl"
   - Translated strings from the new ar files display correctly for header, dashboard, chat, and settings
   - Layout flows right-to-left; check navigation, text alignment, and form controls
   - Run a production build: pnpm build and review the built assets for RTL correctness
5. If any components need additional flipping, add `.rtl-flip` class or logical CSS where necessary.

Notes:
- No secret or credential data is added to the repo.
- The branch was created and pushed automatically by the automation script.
- If CI fails due to missing translations in other modules, copy corresponding en-US/zh-CN files into the ar folder as placeholders and translate iteratively.

If you want reviewers, assignees, or labels added, set the environment variables:
- REVIEWERS="alice,bob"
- ASSIGNEE="alice"
- LABELS="i18n,feature"
- DRAFT=1   (to create a draft PR)
EOF

# Build gh command
GH_CMD=("gh" "pr" "create" "--title" "$PR_TITLE" "--body" "$PR_BODY" "--base" "$REMOTE_DEFAULT" "--head" "$HEAD_BRANCH")

# Add draft flag if requested
if [ "${DRAFT:-0}" = "1" ] || [ "${DRAFT:-0}" = "true" ]; then
  GH_CMD+=("--draft")
fi

# Add labels if provided
if [ -n "${LABELS:-}" ]; then
  IFS=',' read -ra LABS <<< "$LABELS"
  for lab in "${LABS[@]}"; do
    lab_trimmed="$(echo "$lab" | xargs)"
    if [ -n "$lab_trimmed" ]; then
      GH_CMD+=("--label" "$lab_trimmed")
    fi
  done
else
  # default labels
  GH_CMD+=("--label" "i18n" "--label" "feature")
fi

# Add assignee if provided
if [ -n "${ASSIGNEE:-}" ]; then
  GH_CMD+=("--assignee" "$ASSIGNEE")
fi

# Add reviewers if provided
if [ -n "${REVIEWERS:-}" ]; then
  IFS=',' read -ra RV <<< "$REVIEWERS"
  for r in "${RV[@]}"; do
    r_trimmed="$(echo "$r" | xargs)"
    if [ -n "$r_trimmed" ]; then
      GH_CMD+=("--reviewer" "$r_trimmed")
    fi
  done
fi

echo "Creating PR on GitHub..."
echo "Command: ${GH_CMD[*]}"

# Execute the command
set -x
"${GH_CMD[@]}"
set +x

echo "PR creation attempted. If gh reported success, open the created PR in your browser or run 'gh pr view --web'."
