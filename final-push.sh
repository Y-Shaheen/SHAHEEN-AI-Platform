#!/usr/bin/env bash
# final-push.sh
# Zero-touch push with auto-branching and automatic token reading.
# Behavior:
#  - Reads token from environment or known paths (GITHUB_TOKEN, GH_TOKEN, SHAHEEN_TOKEN, ~/.shaheen_token)
#  - Commits any changes (auto-message if not provided)
#  - Attempts to push to the target branch
#  - If push fails (non-fast-forward / conflicts), creates a new branch auto/<timestamp>-<rand> and pushes that instead
#  - Optionally create a PR (requires gh CLI and GH_TOKEN/GITHUB_TOKEN)
#
# Usage:
#   ./final-push.sh [--branch BRANCH] [--message "commit message"] [--remote REMOTE] [--create-pr] [--pr-title "title"] [--pr-body "body"]
#
set -euo pipefail
IFS=$'\n\t'

log() { printf '%s\n' "$*"; }
err() { printf 'ERROR: %s\n' "$*" >&2; }
timestamp() { date -u +"%Y%m%d%H%M%S"; }

# --- Defaults / args ---
TARGET_BRANCH=""
COMMIT_MSG=""
REMOTE_NAME="origin"
CREATE_PR=false
PR_TITLE=""
PR_BODY=""
AUTO_AUTHOR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch) TARGET_BRANCH="$2"; shift 2;;
    --message) COMMIT_MSG="$2"; shift 2;;
    --remote) REMOTE_NAME="$2"; shift 2;;
    --create-pr) CREATE_PR=true; shift;;
    --pr-title) PR_TITLE="$2"; shift 2;;
    --pr-body) PR_BODY="$2"; shift 2;;
    --author) AUTO_AUTHOR="$2"; shift 2;;
    -h|--help) cat <<EOF
Usage: $0 [--branch BRANCH] [--message "commit message"] [--remote REMOTE] [--create-pr] [--pr-title "title"] [--pr-body "body"]
Environment:
  GITHUB_TOKEN or GH_TOKEN or SHAHEEN_TOKEN or file ~/.shaheen_token is used automatically for auth.
EOF
      exit 0;;
    *) err "Unknown arg: $1"; exit 2;;
  esac
done

# --- token discovery ---
discover_token() {
  : "${GITHUB_TOKEN:-}"
  : "${GH_TOKEN:-}"
  : "${SHAHEEN_TOKEN:-}"
  local t=""
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then t="$GITHUB_TOKEN"; fi
  if [[ -z "$t" && -n "${GH_TOKEN:-}" ]]; then t="$GH_TOKEN"; fi
  if [[ -z "$t" && -n "${SHAHEEN_TOKEN:-}" ]]; then t="$SHAHEEN_TOKEN"; fi
  if [[ -z "$t" && -f "${HOME}/.shaheen_token" ]]; then
    t="$(< "${HOME}/.shaheen_token")"
  fi
  # also try git config
  if [[ -z "$t" ]]; then
    t="$(git config --get github.token || true)"
  fi
  echo "$t"
}

TOKEN="$(discover_token || true)"
if [[ -z "${TOKEN// /}" ]]; then
  err "No token found. Set GITHUB_TOKEN, GH_TOKEN, or place token in ~/.shaheen_token or git config github.token"
  exit 3
fi

# --- git repo checks ---
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  err "Not inside a git repository"
  exit 4
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ -z "$TARGET_BRANCH" ]]; then
  TARGET_BRANCH="$CURRENT_BRANCH"
fi

# prepare commit if there are changes
if ! git diff --quiet || ! git ls-files --others --exclude-standard --quiet; then
  # there are changes
  if [[ -z "$COMMIT_MSG" ]]; then
    COMMIT_MSG="auto: sync changes (final-push.sh) @$(timestamp)"
  fi
  log "Staging all changes..."
  git add -A
  if git diff --cached --quiet; then
    log "Nothing to commit after staging."
  else
    if [[ -n "$AUTO_AUTHOR" ]]; then
      git commit -m "$COMMIT_MSG" --author="$AUTO_AUTHOR"
    else
      git commit -m "$COMMIT_MSG"
    fi
    log "Committed changes: $COMMIT_MSG"
  fi
else
  log "Working tree clean; no commit needed."
fi

# get remote URL
REMOTE_URL="$(git remote get-url "$REMOTE_NAME" 2>/dev/null || true)"
if [[ -z "$REMOTE_URL" ]]; then
  err "Remote '$REMOTE_NAME' not found. Use --remote to specify a valid remote."
  exit 5
fi

# convert SSH to HTTPS if necessary
to_https() {
  local url="$1"
  if [[ "$url" =~ ^git@([^:]+):(.+)\.git$ ]]; then
    local host="${BASH_REMATCH[1]}"
    local repo_path="${BASH_REMATCH[2]}"
    echo "https://${host}/${repo_path}.git"
  elif [[ "$url" =~ ^ssh://git@([^/]+)/(.+)\.git$ ]]; then
    echo "https://${BASH_REMATCH[1]}/${BASH_REMATCH[2]}.git"
  else
    echo "$url"
  fi
}

HTTP_URL="$(to_https "$REMOTE_URL")"

# embed token safely for single push (will not modify remote)
# Use x-access-token for GitHub compatibility
AUTH_PUSH_URL="$HTTP_URL"
if [[ "$HTTP_URL" =~ ^https:// ]]; then
  # escape token for URL (basic)
  # Note: this will expose token in process list for a short time; prefer env credential helpers if you are concerned
  ESC_TOKEN="$(printf '%s' "$TOKEN" | sed -e 's/%/%25/g' -e 's/ /%20/g' -e 's/@/%40/g' -e 's/:/%3A/g' -e 's/\//%2F/g')"
  AUTH_PUSH_URL="$(echo "$HTTP_URL" | sed -e "s#https://#https://x-access-token:${ESC_TOKEN}@#")"
else
  err "Unsupported remote URL scheme: $HTTP_URL"
  exit 6
fi

push_to_ref() {
  local push_url="$1"
  local src_ref="$2"
  local dst_ref="$3"
  log "Pushing ${src_ref} -> ${dst_ref} ..."
  if git push --set-upstream "$push_url" "${src_ref}:${dst_ref}"; then
    return 0
  else
    return 1
  fi
}

# Attempt normal push
if push_to_ref "$AUTH_PUSH_URL" "HEAD" "$TARGET_BRANCH"; then
  log "Successfully pushed to ${TARGET_BRANCH}"
  exit 0
fi

log "Push to ${TARGET_BRANCH} failed — creating an auto-branch to preserve your work."

# Create auto-branch name
NEW_BRANCH="auto/push-$(timestamp)-$((RANDOM%10000))"
log "Creating branch ${NEW_BRANCH} from current HEAD..."
git checkout -b "$NEW_BRANCH"

# Attempt push of new branch
if push_to_ref "$AUTH_PUSH_URL" "HEAD" "$NEW_BRANCH"; then
  log "Successfully pushed to new branch: ${NEW_BRANCH}"
  if $CREATE_PR; then
    if command -v gh >/dev/null 2>&1; then
      PR_TITLE_TO_USE="${PR_TITLE:-Auto-merge request: ${NEW_BRANCH} -> ${TARGET_BRANCH}}"
      PR_BODY_TO_USE="${PR_BODY:-This branch was created automatically due to a push conflict when pushing to ${TARGET_BRANCH}.}"
      log "Creating PR via gh CLI: base=${TARGET_BRANCH}, head=${NEW_BRANCH}"
      # set GH_TOKEN for gh if GH_TOKEN not set but we have GITHUB_TOKEN
      if [[ -n "${GITHUB_TOKEN:-}" && -z "${GH_TOKEN:-}" ]]; then
        export GH_TOKEN="$GITHUB_TOKEN"
      fi
      if gh pr create --base "$TARGET_BRANCH" --head "$NEW_BRANCH" --title "$PR_TITLE_TO_USE" --body "$PR_BODY_TO_USE"; then
        log "PR created for ${NEW_BRANCH} -> ${TARGET_BRANCH}"
      else
        err "Failed to create PR via gh. You can create one manually."
      fi
    else
      err "gh CLI not found. Install GitHub CLI to enable --create-pr."
    fi
  fi
  log "Done. Your changes are on branch: ${NEW_BRANCH}"
  exit 0
else
  err "Failed to push new branch ${NEW_BRANCH}. Aborting."
  # try to switch back to original branch for safety
  git checkout - >/dev/null 2>&1 || true
  exit 7
fi