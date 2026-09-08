#!/usr/bin/env bash
# Run after cloning the repository; works from any current directory.
set -eu
# Ubuntu cloud containers can provision their minimal runtime explicitly.
for argument in "$@"; do
  if [ "$argument" = "--install-tools" ]; then
    if ! command -v python3 >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
      if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = 0 ]; then
        if ! apt-get update -qq >/dev/null 2>&1 || ! apt-get install -y -qq python3 git ca-certificates >/dev/null 2>&1; then
          printf '%s\n' 'host runtime: unavailable (Ubuntu package install failed)'
          exit 2
        fi
      fi
    fi
  fi
done
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'python3: unavailable (install Python 3 before cloud setup)'
  exit 2
fi
exec python3 "$(cd "$(dirname "$0")" && pwd)/cloud_setup.py" "$@"
