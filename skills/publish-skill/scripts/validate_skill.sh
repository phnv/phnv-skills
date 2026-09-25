#!/usr/bin/env bash
# Validates a skill folder against the open Agent Skills spec before publishing
# to any channel. Installs skills-ref if it isn't already available.
#
# Usage: ./validate_skill.sh <path-to-skill-folder>

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-skill-folder>" >&2
  exit 1
fi

SKILL_PATH="$1"

if ! command -v agentskills >/dev/null 2>&1; then
  echo "Installing skills-ref (validator) via pipx..."
  pipx install skills-ref --quiet
fi

if [ ! -f "${SKILL_PATH}/SKILL.md" ]; then
  echo "No SKILL.md found at ${SKILL_PATH}/SKILL.md" >&2
  exit 1
fi

echo "Validating ${SKILL_PATH} ..."
if agentskills validate "${SKILL_PATH}"; then
  echo "Passed. Safe to proceed with any publishing channel."
else
  echo "Failed validation above. Fix these before publishing — every channel (git, npm, Claude plugin marketplace) expects this same baseline." >&2
  exit 1
fi
