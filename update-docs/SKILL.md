---
name: update-docs
description: Create, update, validate, and reorganize project docs folders with active feature docs and archived completed/cancelled/paused feature docs. Use when a user asks to set up docs, update docs structure, add active feature docs, mark an active feature as completed/cancelled/paused, complete/archive a feature, cancel or pause a feature, resume paused docs, create PRD/issue/reference docs, or copy this docs convention into another repository.
---

# Update Docs

## Start

Inspect the target project before writing:

```sh
pwd
rg --files docs 2>/dev/null || true
find docs -maxdepth 4 -type d 2>/dev/null | sort || true
git status --short
```

Use the current project root unless the user names another path. Preserve existing docs; do not overwrite customized files unless the user explicitly asks. Leave unrelated dirty worktree changes alone.

## Layout

Use this docs lifecycle layout:

```text
docs/
├── README.md
├── agent-workflow.md
├── feature-reference-template.md
├── <active-feature>/
│   ├── prd.md
│   └── issues/
└── features/
    ├── README.md
    ├── completed/
    │   └── <feature>/
    │       ├── reference.md
    │       ├── prd.md
    │       ├── issues/
    │       └── adr/
    ├── cancelled/
    │   └── <feature>/
    │       ├── decision.md
    │       ├── prd.md
    │       └── issues/
    └── paused/
        └── <feature>/
            ├── handoff.md
            ├── prd.md
            └── issues/
```

Rules:

- Keep active feature PRDs and issue slices directly under `docs/<feature>/`.
- Move completed features to `docs/features/completed/<feature>/`.
- Move cancelled features to `docs/features/cancelled/<feature>/` and record why in `decision.md`.
- Move paused features to `docs/features/paused/<feature>/` and record restart context in `handoff.md`.
- Keep implementation orientation in completed feature `reference.md`.
- Keep execution scope in issue docs.
- Create ADRs only for hard-to-reverse decisions that would be surprising without context.

## Script

Use the script for repeatable scaffold, archive, resume, and validation work:

```sh
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py /path/to/project --project-name "Project Name"
```

Common operations:

```sh
# Initialize common docs files.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py .

# Create active feature docs.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --active-feature route-flyover-v2

# Create archived feature docs directly.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --completed-feature route-flyover
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --cancelled-feature old-search
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --paused-feature onboarding-refresh

# Move active docs into an archive status.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --complete-feature route-flyover-v2
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --cancel-feature route-flyover-v2
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --pause-feature route-flyover-v2

# Equivalent status-neutral form.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --archive-feature route-flyover-v2 --status completed

# Resume paused docs back to active.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --resume-feature route-flyover-v2

# Check expected structure.
python3 /Users/jason/.codex/skills/update-docs/scripts/update_docs.py . --validate
```

Useful options:

- `--force`: overwrite scaffold files only. Do not use unless explicitly requested.
- `--dry-run`: show intended changes without writing.

After running, review generated files and adapt project-specific workflow language, test commands, and archive notes.

## Mark Active Feature

When the user asks to mark, finish, archive, close, cancel, or pause an active feature:

1. Inspect active candidates under `docs/<feature>/` and current git status.
2. If the status is not explicit, ask with a numbered list and wait for the user to choose exactly one:
   - `completed`: move to `docs/features/completed/<feature>/` and create `reference.md`.
   - `cancelled`: move to `docs/features/cancelled/<feature>/` and create `decision.md`.
   - `paused`: move to `docs/features/paused/<feature>/` and create `handoff.md`.
3. Move files only after the user's answer is clear.
4. Run the script with `--archive-feature <feature> --status <completed|cancelled|paused>`.
5. If completed, open `docs/features/completed/<feature>/reference.md` and fill it from the PRD, issue docs, ADRs, current code map, test commands, known gaps, and future-change guidance. Do not leave the generated template untouched when project context is discoverable.
6. If cancelled, fill `decision.md` with the reason, current state, and what should not be resumed accidentally.
7. If paused, fill `handoff.md` with current state, first restart actions, blockers, and verification caveats.
8. Run validation and a stale-link search before reporting completion.

## Manual Reorganization

When converting existing docs:

1. Inventory current files with `rg --files docs`.
2. Identify active feature folders and archived feature folders.
3. Move active work to `docs/<feature>/`.
4. Move completed work to `docs/features/completed/<feature>/`.
5. Move cancelled work to `docs/features/cancelled/<feature>/`.
6. Move paused work to `docs/features/paused/<feature>/`.
7. Update stale links with `rg -n "docs/(prd|issues|adr)|docs/features/[^/]+/(prd|issues|adr|reference)|PROMPT.md" docs`.
8. Leave unrelated generated files and existing dirty worktree changes alone.

Prefer filesystem moves if `.git` is read-only; Git can detect renames later.

## Finish

Report created or moved paths, skipped files, validation warnings, stale-link checks, and any customized files left untouched. If official skill validation is unavailable because PyYAML is missing, say so and use a basic YAML/frontmatter check instead.
