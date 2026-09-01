---
name: hermes-bundled-skills-sync
description: "Understand and troubleshoot Hermes Agent bundled-skills seeding, startup sync, and overwrite protection"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, sync, bundled, devcontainer, troubleshooting]
    related_skills: [hermes-agent]
---
# Hermes Bundled Skills Sync

## Overview
Hermes installs ~81 bundled skills into `~/.hermes/skills`. On every startup it re-syncs them from the bundled tree (`hermes_cli/main.py` → `_sync_bundled_skills_for_startup()`/`_sync_bundled_skills_quietly()` → `tools/skills_sync.py::sync_skills`), tracked by a manifest (`.bundled_manifest`, format `skill_name:origin_hash` = MD5 at sync time; v1 plain-name manifests auto-migrate).

## Sync rules (overwrite protection)
| State | Behavior |
|---|---|
| Bundled unchanged since last sync | skip |
| Bundled changed & local unedited | **update (only automatic overwrite)** |
| Bundled changed & local edited | skip & keep (user-modified, permanently protected) |
| In manifest but absent from disk | treat as user-deleted; not re-added |
| `.no-bundled-skills` marker | skip all bundled seeding except essential skills |

User edits are **never** auto-overwritten. Explicit overwrite only via `hermes skills reset <name> --restore` or `hermes skills update --force`. `HERMES_BUNDLED_SKILLS` points at a custom bundled-skill tree (Homebrew/Nix).

## Why deleted skills reappear (devcontainer gotcha)
In Dev Containers the image seeds all bundled skills into `~/.hermes/skills`, and a `postCreateCommand` (e.g. `setup-skills.sh`) copies them into the git repo:
```bash
cp -a --update=none "$HOME/.hermes/skills"/. /workdir/skills/
rm -rf "$HOME/.hermes/skills" && ln -sfn /workdir/skills "$HOME/.hermes/skills"
```
`--update=none` is **no-clobber**: it copies only files missing at the destination. Deleting a bundled category (e.g. `skills/apple`) from git makes it "missing", so the image-seeded copy is re-added on every container start — deletion cannot be persisted this way.

## Troubleshooting
- **Deleted skills keep coming back** → caused by image seeding + no-clobber `cp` in the setup script, not by Hermes itself. Give up on deleting bundled skills from a git-managed copy, or mount a separate user-skills dir.
- **Will my edits be overwritten?** → No. `--update=none` skips existing files, and `sync_skills` hash comparison protects edited skills.
