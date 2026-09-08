#!/usr/bin/env bash
# ensure-commands.sh: make the session commands and the voice guide present in a
# cloud cockpit env, or say loudly why not.
#
# The problem it solves, found 27 Jul 2026. /start, /done, /checkpoint and /ship
# are not in this repo. On the Mac they resolve through ~/.claude/commands/,
# which are symlinks into total-audio-platform/.claude/global-commands/. A cloud
# cockpit sandbox clones this repo and the vault and nothing else, so on the
# phone those four commands simply do not exist. Same for brand-voice-guide,
# which CLAUDE.md's writing rule points at by a cross-repo path that has never
# resolved in the cloud.
#
# total-audio-platform stays the single source of truth. This syncs FROM it
# rather than forking it, so editing /done in TAP keeps working and the phone
# picks the change up at next boot. Nothing is copied into this repo.
#
# Idempotent and safe to run at any point in a session. Two callers:
#   1. scripts/setup/cloud-env-setup.sh (container boot)
#   2. the SessionStart hook in .claude/settings.json (every session)
#
# The second is the self-heal, same as ensure-vault.sh: if boot-time setup never
# ran, the session still gets its commands.
#
# On the Mac this is a deliberate no-op. The real symlinks are already there and
# are truth; overwriting them with copies would be a downgrade.
#
# Always exits 0. Missing commands degrade a session; they must never block one.

set -uo pipefail

CMD_DIR="${CLAUDE_CMD_DIR:-$HOME/.claude/commands}"
SKILL_DIR="${CLAUDE_SKILL_DIR:-$HOME/.claude/skills}"
TAP_REMOTE="${TAP_REMOTE:-github.com/chrisschouk/total-audio-platform.git}"
WORK_DIR="${TAP_SPARSE_DIR:-$HOME/.cache/cockpit-tap-commands}"

# Session commands and their direct skill dependencies travel together.
# Product work runs in the target repository with its own setup contract.
#
# The four session commands live in .claude/global-commands/ but weekly-review
# lives in .claude/commands/, so each name is resolved against both directories
# rather than assuming one. Verified 27 Jul 2026 by listing both.
COMMANDS="start.md done.md checkpoint.md ship.md weekly-review.md"
SKILLS="brand-voice-guide commodity-gate home"

export GIT_TERMINAL_PROMPT=0

say()  { echo "[commands] $*"; }
warn() { echo "[commands] WARN: $*"; }

scrub() { sed -e 's#x-access-token:[^@]*@#x-access-token:***@#g'; }
reason() { printf '%s' "$1" | scrub | grep -v '^[[:space:]]*$' | tail -1; }

# On the Mac the commands are symlinks into the TAP working copy, which is truth
# and is always fresher than any clone. Leave them alone.
if [ -L "$CMD_DIR/start.md" ]; then
  say "local symlinks present, TAP working copy is truth. No sync needed."
  exit 0
fi

# A working copy on disk beats a network clone, and costs nothing.
#
# Found 22 Aug 2026. This script quit at the token gate below in a session where
# total-audio-platform was cloned two directories away, so brand-voice-guide was
# absent and CLAUDE.md's writing rule — which names that skill and says it is
# synced here at session start — was silently unenforceable. That is the exact
# fault the rule's own comment records for 23-27 Jul, recurring because the only
# source this script would accept was one it had to authenticate to reach.
#
# Cloud envs that clone the portfolio have TAP on disk. Use it.
LOCAL_TAP=""
for candidate in "${TAP_LOCAL:-}" \
                 "${CLAUDE_PROJECT_DIR:-$PWD}" \
                 "$(dirname "${CLAUDE_PROJECT_DIR:-$PWD}")/total-audio-platform" \
                 "$HOME/total-audio-platform" \
                 "$HOME/code/total-audio-platform"; do
  [ -n "$candidate" ] || continue
  if [ -f "$candidate/.claude/global-commands/start.md" ] && [ -f "$candidate/.claude/global-commands/done.md" ] && [ -d "$candidate/.claude/skills" ]; then LOCAL_TAP="$candidate"; break; fi
done

if [ -n "$LOCAL_TAP" ]; then
  WORK_DIR="$LOCAL_TAP"
  say "using the working copy at $LOCAL_TAP, no clone needed."
elif [ -z "${TAP_GITHUB_TOKEN:-}" ]; then
  warn "TAP_GITHUB_TOKEN not set and no total-audio-platform on disk."
  warn "No /start, /done, /checkpoint, /ship or voice guide this session."
  warn "Sessions still work; they just lose the startup and close-out workflows."
  exit 0
fi

if [ -z "$LOCAL_TAP" ]; then
# Keep credentials out of clone URLs and .git/config, including failed clones.
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader
export GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$TAP_GITHUB_TOKEN" | base64 | tr -d '\n')"
AUTH_URL="https://${TAP_REMOTE}"

# Sparse clone: TAP is a large monorepo and we want two directories from it.
if [ ! -d "$WORK_DIR/.git" ]; then
  mkdir -p "$(dirname "$WORK_DIR")"
  if ! err="$(git clone --depth 1 --filter=blob:none --sparse "$AUTH_URL" "$WORK_DIR" 2>&1)"; then
    warn "clone failed, no commands this session: $(reason "$err")"
    warn "If this repeats, check the PAT can read total-audio-platform and not just the vault."
    exit 0
  fi
  git -C "$WORK_DIR" sparse-checkout set .claude/global-commands .claude/commands .claude/skills .claude/agents >/dev/null 2>&1
  git -C "$WORK_DIR" remote set-url origin "https://${TAP_REMOTE}" 2>/dev/null
else
  if ! err="$(git -C "$WORK_DIR" fetch --depth 1 "$AUTH_URL" HEAD 2>&1)"; then
    warn "fetch failed, using a possibly stale copy: $(reason "$err")"
  else
    git -C "$WORK_DIR" reset --hard FETCH_HEAD >/dev/null 2>&1 \
      || warn "could not fast-forward the command cache; copies may be stale"
  fi
fi
fi

SRC_GLOBAL="$WORK_DIR/.claude/global-commands"
SRC_LOCAL="$WORK_DIR/.claude/commands"
SRC_SKILL="$WORK_DIR/.claude/skills"

if [ ! -d "$SRC_GLOBAL" ] && [ ! -d "$SRC_LOCAL" ]; then
  warn "neither .claude/global-commands nor .claude/commands is in the clone."
  warn "TAP's layout moved; this script needs updating."
  exit 0
fi

mkdir -p "$CMD_DIR" "$SKILL_DIR"

copied=0
missing=""
for c in $COMMANDS; do
  if [ -f "$SRC_GLOBAL/$c" ]; then
    cp -f "$SRC_GLOBAL/$c" "$CMD_DIR/$c" && copied=$((copied + 1))
  elif [ -f "$SRC_LOCAL/$c" ]; then
    cp -f "$SRC_LOCAL/$c" "$CMD_DIR/$c" && copied=$((copied + 1))
  else
    missing="$missing $c"
  fi
done

skills_copied=0
for s in $SKILLS; do
  if [ -d "$SRC_SKILL/$s" ]; then
    rm -rf "${SKILL_DIR:?}/$s"
    cp -RL "$SRC_SKILL/$s" "$SKILL_DIR/$s" && skills_copied=$((skills_copied + 1))
  else
    missing="$missing $s"
  fi
done

# Adjacent references are part of the command contract, not optional prose.
for reference in "$SRC_GLOBAL"/*reference*.md; do
  [ -f "$reference" ] && cp -f "$reference" "$CMD_DIR/"
done
# The home skill names repo agent definitions. Keep those available together.
if [ -d "$WORK_DIR/.claude/agents" ]; then
  mkdir -p "${CLAUDE_AGENT_DIR:-$HOME/.claude/agents}"
  cp -RL "$WORK_DIR/.claude/agents/." "${CLAUDE_AGENT_DIR:-$HOME/.claude/agents}/"
fi

say "synced $copied commands and $skills_copied skills from total-audio-platform @ $(git -C "$WORK_DIR" log -1 --format='%h %ad' --date=short 2>/dev/null || echo unknown)"
[ -n "$missing" ] && warn "not found in TAP, skipped:$missing"

exit 0
