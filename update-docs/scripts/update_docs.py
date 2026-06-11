#!/usr/bin/env python3
"""Create, update, archive, and validate a project docs folder."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ARCHIVE_STATUSES = ("completed", "cancelled", "paused")


def slug_to_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", slug) if part)


def record(results: list[str], message: str) -> None:
    results.append(message)


def ensure_dir(path: Path, dry_run: bool, results: list[str]) -> None:
    if path.exists():
        record(results, f"exists {path}")
        return
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)
    record(results, f"created {path}")


def write_file(path: Path, content: str, force: bool, dry_run: bool, results: list[str]) -> None:
    if path.exists():
        if path.read_text() == content:
            record(results, f"unchanged {path}")
        elif force:
            if not dry_run:
                path.write_text(content)
            record(results, f"updated {path}")
        else:
            record(results, f"skipped {path} (exists)")
        return

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    record(results, f"created {path}")


def docs_readme(project_name: str) -> str:
    return f"""# {project_name} Docs

Use `agent-workflow.md` for the session workflow.

Active feature docs live directly under `docs/` as `docs/<feature>/`:

- `<feature>/prd.md`: active PRD or planning doc.
- `<feature>/issues/`: local implementation slices.

Archived feature docs live under `features/`:

- `features/completed/<feature>/`: shipped or no-longer-active completed features.
- `features/cancelled/<feature>/`: stopped features with a decision note.
- `features/paused/<feature>/`: temporarily parked features with restart context.

Use `feature-reference-template.md` for completed feature references.

Keep glossary or terminology docs separate from implementation references when the project has a glossary.
"""


def agent_workflow() -> str:
    return """## Session Inputs

Inputs arrive in chat:
- handoff path or pasted handoff, if any
- recent work summary, if any
- target issue/task

Start:
- Read `AGENTS.md` first, if present.
- If a handoff path is provided, read it before planning.
- If the target issue/task is missing or ambiguous, ask concise clarification before proceeding.
- Let the latest chat instruction override older handoff, PRD, issue, or doc text.

## Working Rules

- Do one issue at a time. Do not batch adjacent issues.
- Inspect the real code, docs, current diff, and relevant commits before planning.
- Ask before broad refactors, schema changes, data migrations, required fields, backfills, or public API contract changes.
- If an answer is discoverable from code/docs, inspect instead of asking.
- Keep active feature docs under `docs/<feature>/`.
- Move completed feature docs under `docs/features/completed/<feature>/`.
- Move cancelled feature docs under `docs/features/cancelled/<feature>/`.
- Move paused feature docs under `docs/features/paused/<feature>/`.
- Create ADRs only for hard-to-reverse decisions that would be surprising without context.
- Do not stage, commit, or push without explicit user confirmation.

## Issue Workflow

1. Review relevant handoff, docs, issue text, commits, and current diff.
2. Explore implementation seams and risks.
3. Present a concise implementation plan before edits:
   - behavior to deliver
   - public interface or user-visible behavior
   - tests to write
   - risky assumptions or questions
   - verification plan
4. Use vertical TDD when requested:
   - write one failing behavior test
   - implement the minimum code to pass
   - repeat for the next behavior
   - refactor only while green
5. Run focused automated tests.
6. Provide manual tests when useful.
7. Finish with a concise summary:
   - files changed
   - tests run and results
   - manual test checklist
   - remaining risks
   - recommended commit scope and message
8. Ask the user whether to stage and commit the verified implementation.
"""


def features_readme() -> str:
    return """# Feature Archive

This folder contains feature docs that are not the active planning surface. Active feature PRDs and issue slices live directly under `docs/<feature>/`.

## Status Folders

- `completed/`: shipped or otherwise complete features that future agents may need to understand.
- `cancelled/`: stopped features with a decision note explaining why work ended.
- `paused/`: temporarily parked features with a handoff for resuming later.

## Completed Feature Standard

Each completed feature should include:

- `reference.md`: current feature orientation for future agents.
- `prd.md`: completed PRD.
- `issues/`: completed issue slices.
- `adr/`: feature-level decisions, when needed.

Use [../feature-reference-template.md](../feature-reference-template.md) for completed feature docs.
"""


def status_readme(status: str) -> str:
    descriptions = {
        "completed": "Features that shipped or are otherwise complete enough to serve as historical reference.",
        "cancelled": "Features intentionally stopped. Each folder should explain why work ended and what should not be resumed accidentally.",
        "paused": "Features temporarily parked. Each folder should include enough restart context to resume later.",
    }
    return f"""# {status.capitalize()} Features

{descriptions[status]}
"""


def feature_reference_template() -> str:
    return """# <Feature Name> Feature Reference

Source point: `<commit sha>` `<commit subject>`
Last updated: `<date>`
Status: `<landed | partial | deprecated>`

## Purpose

Explain what this doc is for and which future sessions should read it first.

## Source Docs

- Glossary: `<path, if any>`
- PRD: `docs/features/completed/<feature>/prd.md`
- ADRs: `docs/features/completed/<feature>/adr/`
- Issues: `docs/features/completed/<feature>/issues/`

## Current Contract

Describe the user-facing behavior that must remain true.

## Non-Goals

List nearby concepts or tempting extensions that are intentionally out of scope.

## Code Map

List the main files and what each owns. Keep this at the seam level rather than documenting every function.

## Lifecycle

Describe the ordered flow from entry to cleanup or persistence.

## Stable Contracts

List pure logic contracts, data-shape rules, timing rules, API boundaries, or UI invariants that future changes should preserve.

## Testing

List fast tests, broader tests, manual validation, and known environmental caveats.

## Known Gaps

List pending validation, follow-up issues, or intentionally unfinished behavior.

## Future Change Guidance

Explain where to add new behavior, what to avoid, and what docs should be updated alongside code changes.
"""


def prd_template(title: str) -> str:
    return f"""# PRD: {title}

## Problem Statement

Describe the user or business problem.

## Solution

Describe the proposed behavior and scope.

## User Stories

- As a user, I want ...

## Implementation Decisions

Record decisions that affect implementation shape.

## Testing Decisions

Record required automated and manual validation.

## Out of Scope

List adjacent work that should not be included.
"""


def completed_reference(title: str, slug: str) -> str:
    return feature_reference_template().replace("<Feature Name>", title).replace("<feature>", slug)


def decision_template(title: str) -> str:
    return f"""# Cancelled: {title}

Status: cancelled
Date: `<date>`

## Decision

Explain why this feature was cancelled.

## Context

Summarize the state of the work when it stopped.

## Do Not Resume Without

List the decision, dependency, or product change required before reopening this feature.
"""


def handoff_template(title: str) -> str:
    return f"""# Paused: {title}

Status: paused
Date: `<date>`

## Current State

Summarize what exists and what remains incomplete.

## Immediate Next Steps

List the first actions for a future session.

## Important Context

Capture constraints, blockers, decisions, and verification caveats.
"""


def ensure_common_docs(root: Path, project_name: str, force: bool, dry_run: bool, results: list[str]) -> None:
    docs = root / "docs"
    write_file(docs / "README.md", docs_readme(project_name), force, dry_run, results)
    write_file(docs / "agent-workflow.md", agent_workflow(), force, dry_run, results)
    write_file(docs / "feature-reference-template.md", feature_reference_template(), force, dry_run, results)
    write_file(docs / "features" / "README.md", features_readme(), force, dry_run, results)
    for status in ARCHIVE_STATUSES:
        write_file(docs / "features" / status / "README.md", status_readme(status), force, dry_run, results)


def create_active_feature(root: Path, slug: str, force: bool, dry_run: bool, results: list[str]) -> None:
    docs = root / "docs"
    title = slug_to_title(slug)
    ensure_dir(docs / slug / "issues", dry_run, results)
    write_file(docs / slug / "prd.md", prd_template(title), force, dry_run, results)


def create_archived_feature(root: Path, slug: str, status: str, force: bool, dry_run: bool, results: list[str]) -> None:
    base = root / "docs" / "features" / status / slug
    title = slug_to_title(slug)
    ensure_dir(base / "issues", dry_run, results)
    write_file(base / "prd.md", prd_template(title), force, dry_run, results)

    if status == "completed":
        ensure_dir(base / "adr", dry_run, results)
        write_file(base / "reference.md", completed_reference(title, slug), force, dry_run, results)
    elif status == "cancelled":
        write_file(base / "decision.md", decision_template(title), force, dry_run, results)
    elif status == "paused":
        write_file(base / "handoff.md", handoff_template(title), force, dry_run, results)
    else:
        raise ValueError(f"unknown status: {status}")


def replace_links(root: Path, old: str, new: str, dry_run: bool, results: list[str]) -> None:
    docs = root / "docs"
    if not docs.exists():
        return
    for path in docs.rglob("*.md"):
        text = path.read_text()
        changed = text.replace(old, new)
        if changed != text:
            if not dry_run:
                path.write_text(changed)
            record(results, f"updated links in {path}")


def move_active_to_archive(root: Path, slug: str, status: str, dry_run: bool, results: list[str]) -> None:
    source = root / "docs" / slug
    destination = root / "docs" / "features" / status / slug
    if not source.exists():
        record(results, f"skipped {source} (missing)")
        return
    if destination.exists():
        record(results, f"skipped {destination} (exists)")
        return

    ensure_dir(destination.parent, dry_run, results)
    if not dry_run:
        shutil.move(str(source), str(destination))
    record(results, f"moved {source} -> {destination}")

    title = slug_to_title(slug)
    if status == "completed":
        ensure_dir(destination / "adr", dry_run, results)
        write_file(destination / "reference.md", completed_reference(title, slug), False, dry_run, results)
    elif status == "cancelled":
        write_file(destination / "decision.md", decision_template(title), False, dry_run, results)
    elif status == "paused":
        write_file(destination / "handoff.md", handoff_template(title), False, dry_run, results)

    replace_links(root, f"docs/{slug}/", f"docs/features/{status}/{slug}/", dry_run, results)


def resume_paused_feature(root: Path, slug: str, dry_run: bool, results: list[str]) -> None:
    source = root / "docs" / "features" / "paused" / slug
    destination = root / "docs" / slug
    if not source.exists():
        record(results, f"skipped {source} (missing)")
        return
    if destination.exists():
        record(results, f"skipped {destination} (exists)")
        return

    if not dry_run:
        shutil.move(str(source), str(destination))
    record(results, f"moved {source} -> {destination}")
    replace_links(root, f"docs/features/paused/{slug}/", f"docs/{slug}/", dry_run, results)


def validate_docs(root: Path) -> list[str]:
    docs = root / "docs"
    warnings: list[str] = []
    required = [
        docs / "README.md",
        docs / "agent-workflow.md",
        docs / "feature-reference-template.md",
        docs / "features" / "README.md",
    ]
    for path in required:
        if not path.exists():
            warnings.append(f"missing {path}")

    for status in ARCHIVE_STATUSES:
        status_dir = docs / "features" / status
        if not status_dir.exists():
            warnings.append(f"missing {status_dir}")
            continue
        if not (status_dir / "README.md").exists():
            warnings.append(f"missing {status_dir / 'README.md'}")

    if docs.exists():
        for child in docs.iterdir():
            if not child.is_dir() or child.name == "features":
                continue
            if not (child / "prd.md").exists():
                warnings.append(f"missing active PRD {child / 'prd.md'}")
            if not (child / "issues").exists():
                warnings.append(f"missing active issues dir {child / 'issues'}")

        completed = docs / "features" / "completed"
        if completed.exists():
            for feature in completed.iterdir():
                if not feature.is_dir():
                    continue
                if not (feature / "reference.md").exists():
                    warnings.append(f"missing completed reference {feature / 'reference.md'}")

        cancelled = docs / "features" / "cancelled"
        if cancelled.exists():
            for feature in cancelled.iterdir():
                if feature.is_dir() and not (feature / "decision.md").exists():
                    warnings.append(f"missing cancellation decision {feature / 'decision.md'}")

        paused = docs / "features" / "paused"
        if paused.exists():
            for feature in paused.iterdir():
                if feature.is_dir() and not (feature / "handoff.md").exists():
                    warnings.append(f"missing paused handoff {feature / 'handoff.md'}")

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to receive docs/")
    parser.add_argument("--project-name", help="Display name for docs/README.md")
    parser.add_argument("--active-feature", action="append", default=[], help="Feature slug to create under docs/<feature>/")
    parser.add_argument("--completed-feature", action="append", default=[], help="Feature slug to create under docs/features/completed/<feature>/")
    parser.add_argument("--cancelled-feature", action="append", default=[], help="Feature slug to create under docs/features/cancelled/<feature>/")
    parser.add_argument("--paused-feature", action="append", default=[], help="Feature slug to create under docs/features/paused/<feature>/")
    parser.add_argument("--complete-feature", action="append", default=[], help="Move active docs/<feature>/ to docs/features/completed/<feature>/")
    parser.add_argument("--cancel-feature", action="append", default=[], help="Move active docs/<feature>/ to docs/features/cancelled/<feature>/")
    parser.add_argument("--pause-feature", action="append", default=[], help="Move active docs/<feature>/ to docs/features/paused/<feature>/")
    parser.add_argument("--archive-feature", action="append", default=[], help="Move active docs/<feature>/ to docs/features/<status>/<feature>/")
    parser.add_argument("--status", choices=ARCHIVE_STATUSES, help="Archive status for --archive-feature")
    parser.add_argument("--resume-feature", action="append", default=[], help="Move docs/features/paused/<feature>/ back to docs/<feature>/")
    parser.add_argument("--validate", action="store_true", help="Validate expected docs structure")
    parser.add_argument("--force", action="store_true", help="Overwrite existing scaffold files")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    if args.archive_feature and not args.status:
        parser.error("--archive-feature requires --status")
    if args.status and not args.archive_feature:
        parser.error("--status requires --archive-feature")

    root = Path(args.project_root).expanduser().resolve()
    project_name = args.project_name or root.name
    results: list[str] = []

    ensure_common_docs(root, project_name, args.force, args.dry_run, results)

    for slug in args.active_feature:
        create_active_feature(root, slug, args.force, args.dry_run, results)
    for slug in args.completed_feature:
        create_archived_feature(root, slug, "completed", args.force, args.dry_run, results)
    for slug in args.cancelled_feature:
        create_archived_feature(root, slug, "cancelled", args.force, args.dry_run, results)
    for slug in args.paused_feature:
        create_archived_feature(root, slug, "paused", args.force, args.dry_run, results)

    for slug in args.complete_feature:
        move_active_to_archive(root, slug, "completed", args.dry_run, results)
    for slug in args.cancel_feature:
        move_active_to_archive(root, slug, "cancelled", args.dry_run, results)
    for slug in args.pause_feature:
        move_active_to_archive(root, slug, "paused", args.dry_run, results)
    for slug in args.archive_feature:
        move_active_to_archive(root, slug, args.status, args.dry_run, results)
    for slug in args.resume_feature:
        resume_paused_feature(root, slug, args.dry_run, results)

    for result in results:
        print(result)

    if args.validate:
        warnings = validate_docs(root)
        if warnings:
            print("validation warnings:")
            for warning in warnings:
                print(f"- {warning}")
            return 1
        print("validation ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
