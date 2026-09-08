#!/usr/bin/env bash
# Persist only the command search path for subsequent hosted-session commands.
set -eu
[ "${CLAUDE_CODE_REMOTE:-}" = true ] || exit 0
if [ -z "${CLAUDE_ENV_FILE:-}" ]; then
  printf '%s\n' 'cloud PATH: unavailable (SessionStart environment file missing)' >&2
  exit 2
fi
task_project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ ! -f "$task_project_dir/scripts/setup/cloud-contract.json" ]; then
  printf '%s\n' 'cloud PATH: unavailable (repository cloud contract missing)' >&2
  exit 2
fi
task_command_path="$task_project_dir/scripts/setup:$HOME/.local/bin:$PATH"
printf 'export PATH=%q\n' "$task_command_path" >> "$CLAUDE_ENV_FILE"
printf '%s\n' 'cloud PATH: configured for subsequent session commands'
