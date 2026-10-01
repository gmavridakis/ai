# 0001: Adopt the prompt-writing conventions of mattpocock/skills

Date: 2026-10-01. Status: accepted.

## Context

The repo had eleven skills written to a value bar that lived only inside the scheduled-task prompt (`SCHEDULED-TASK.md`): delta test, no duplication of global rules, three hard artifacts, falsifiable steps, under 150 lines with a worked example. A review of [mattpocock/skills](https://github.com/mattpocock/skills) (MIT, 27 shipped skills plus a written author guide, `writing-for-agents`) found several techniques that make a skill behave more predictably and that the bar did not cover:

- the description as a *context pointer* kept short (theirs average 30 words; ours averaged 130);
- user-invoked skills (`disable-model-invocation: true`) that cost no context;
- composition as operative instructions (`Call the Skill tool with "<name>"`) instead of prose hand-offs;
- a completion criterion at the end of every phase, with a hard gate ("no red command, no phase 2");
- literal output templates; leading words; the no-op and cache-vs-environment pruning tests;
- repo hygiene: a `CLAUDE.md` in the repo carrying the invariants, ADRs, a changelog, a credits block for borrowed skills, and a ban on em-dashes in prose.

Several of their skill *bodies* would fail this repo's delta test (`tdd`, `codebase-design`, `implement` are mostly principles), and their skills assume a human typing slash commands while ours assume autonomous triggering across a polyglot enterprise stack. The techniques transfer; most of the content does not, yet.

## Decision

1. Write the author guide into the repo as `docs/conventions.md`, pointed at by a root `CLAUDE.md`, so a manual session and the daily routine follow the same rules.
2. Enforce the mechanical rules with `scripts/lint-skills.py`: description length, boundary clause, `**Done when**` per numbered phase, example present, 150-line cap, no em-dashes, operative hand-offs for siblings named in the boundary, credits block shape.
3. Rewrite all existing skills to the conventions in one pass (this ADR's commit series), keeping their tables, thresholds, commands, and examples: the repo's character stays a diagnostic field manual.
4. Keep every existing skill model-invoked. User-invoked skills arrive with phase 2 (workflow skills adapted from mattpocock/skills), each carrying a credits block.
5. Add `CHANGELOG.md`; the routine appends one line per change.

## Consequences

- Descriptions shrink from ~130 to at most 70 words, so the always-loaded cost (the native skill listing plus `INDEX.md`) falls by roughly half.
- Every numbered phase now ends in an observable state, which is also the hook an evaluation harness can grade against.
- The scheduled-task prompt in `SCHEDULED-TASK.md` changes: its value bar and conflict rules now point at `docs/conventions.md`, and it runs the linter before committing. The stored prompt in the desktop app must be re-pasted from that file.

## Open question: is INDEX.md loaded twice?

Claude Code injects the name and description of every skill under `~/.claude/skills` into the system prompt (that is how auto-invocation works). If so, the `@~/.claude/skills/INDEX.md` import in `~/.claude/CLAUDE.md` puts the same text into context a second time on every prompt. Verify with `/context` in a fresh session. If confirmed, drop the import line from the installers and keep `INDEX.md` as the human-facing table; the description cap then becomes the only lever on context load.

## Phase 2 (not started)

Migrate content from mattpocock/skills onto the roadmap, in this order, each as an adapted skill with credits: `grilling` → requirements-clarification; two-axis `code-review` → code-review-checklist; `tdd` merged with debug-from-raw-logs' failure-rate table → test-first-fixes; `diagnosing-bugs`' loop gate → folded into debug-from-raw-logs; then `pr`, `handoff`, `retro`. Prerequisite, before the first migration: a local evaluation harness that runs a skill against recorded cases and grades the **Done when** states, so every migrated or refined skill has a pass rate before it is committed.
