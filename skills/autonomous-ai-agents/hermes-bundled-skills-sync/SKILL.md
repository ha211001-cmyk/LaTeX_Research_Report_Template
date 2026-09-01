---
name: hermes-bundled-skills-sync
description: "Why Hermes bundled skills reappear, when sync overwrites them, and how manifest hashing protects your edits"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, bundled-skills, sync, devcontainer, troubleshooting]
    related_skills: [hermes-agent]
---

# Hermes Bundled Skills Sync — Troubleshooting

## Overview
Hermes seeds ~80 bundled skills (apple, email, media, social-media, ...) into `~/.hermes/skills` at install and re-syncs them on every startup (`hermes_cli/main.py::_sync_bundled_skills_for_startup` / `_sync_bundled_skills_quietly` → `tools/skills_sync.py::sync_skills`). This explains why deleting bundled skills "doesn't stick" and why your edits are never silently overwritten.

## Why deleted skills come back
1. The Docker image (`.devcontainer/Dockerfile`) bakes the bundled skills into an image layer, first-seeding `~/.hermes/skills` at install time.
2. `devcontainer.json` `postCreateCommand` runs `.devcontainer/setup-skills.sh`, which copies the whole skills tree into the git repo with `cp -a --update=none` (no-clobber) and symlinks `~/.hermes/skills -> /workdir/skills`.
   - `--update=none` = "copy only files absent at the destination" → skills you deleted from git count as "absent" and are restored from the image.
   - Existing files are never overwritten by this step.

## When existing skills ARE/AREN'T overwritten
`sync_skills` manifest logic (`.bundled_manifest`, per-skill origin hash):
- Bundled skill unchanged → skip entirely.
- Bundled changed AND local unmodified (hash matches manifest) → updated. This is the only automatic overwrite path.
- Bundled changed AND local edited → skipped and kept (user-modified protection). Edits are protected forever unless you explicitly run:
  - `hermes skills reset <name> --restore` (discard edits)
  - `hermes skills update --force` (force overwrite)

## Key takeaways
- Edit skills under the git-managed `/workdir/skills` freely — the sync never overwrites your changes.
- Deleting a bundled category from git only "sticks" if you also prevent the image seeding, e.g. accept the no-clobber copy-back or stop shipping the bundled skills in the image.
- `.bundled_manifest` hashes change on `hermes update` — an expected git diff.
- Confirm current state with: `ls -l ~/.hermes/skills` (symlink? real dir?) and `git status skills/`.
