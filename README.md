# ai — reusable Claude skills

A library of small, focused skills that are live in every Claude Code session on this machine. Each skill is a folder under `skills/` containing a `SKILL.md`: YAML frontmatter (`name`, `description`) followed by imperative checklist instructions Claude follows when the skill fires.

## Layout

```
skills/<name>/SKILL.md      one skill per folder; optional references/ for long detail
skills/INDEX.md             generated one-row-per-skill index; the only file always in context
scripts/gen-index.py        regenerates INDEX.md from frontmatter (fails if a boundary clause is missing)
ROADMAP.md                  ordered checklist of skills still to be written
install.ps1 / install.sh    one-shot wiring for Windows / POSIX (see below)
README.md                   this file
```

## Skills

| Name | Fires when | Does not fire when |
| --- | --- | --- |
| [bug-report-writing](skills/bug-report-writing/SKILL.md) | The user asks to file, report, or write up a bug for people who cannot see this conversation (upstream issue, other team, vendor ticket) | The goal is to diagnose or fix it here (error-triage, debug-from-raw-logs) |
| [context-hygiene](skills/context-hygiene/SKILL.md) | A task touches many or large files, a tool result is long, or the session nears its auto-compact window | The question is the wording/length of the reply (token-optimizer) |
| [debug-from-raw-logs](skills/debug-from-raw-logs/SKILL.md) | A bug/crash/failing test is reported and a fix would otherwise be guessed from the description | Feature requests; errors whose cause is already printed; layer still unknown (error-triage); a Spring/Hibernate tell listed in java-spring-stack |
| [error-triage](skills/error-triage/SKILL.md) | An error, status code, or "it fails" report arrives and the failing layer is unknown | The layer is established (debug-from-raw-logs; java-spring-stack first for Java/Spring) |
| [java-spring-stack](skills/java-spring-stack/SKILL.md) | Code is written, reviewed, or fixed in a Java / Spring Boot / Hibernate-JPA / JAX-RS / JAX-WS project, or a stack-specific symptom appears (LazyInitializationException, N+1, @Transactional not rolling back, javax→jakarta errors) | The failing layer is still unknown (error-triage); the generic reproduce/bisect procedure (debug-from-raw-logs); other stacks |
| [nodejs](skills/nodejs/SKILL.md) | Code is written, reviewed, or fixed in a Node.js project (package.json present), or a Node-specific symptom appears (ERR_REQUIRE_ESM, ERR_MODULE_NOT_FOUND, unhandled rejection crash, ERESOLVE, heap OOM, event-loop lag, SIGTERM ignored) | The failing layer is still unknown (error-triage); the generic reproduce/bisect procedure (debug-from-raw-logs); Java/Spring (java-spring-stack); browser-only React/Angular code |
| [python-django](skills/python-django/SKILL.md) | Code is written, reviewed, or fixed in a Python / Django (DRF, Celery, ASGI) project — manage.py or `django` in requirements present — or a Django-specific symptom appears (ImproperlyConfigured settings, AppRegistryNotReady, unapplied/conflicting migrations, SynchronousOnlyOperation, TransactionManagementError, NoReverseMatch, staticfiles manifest, CSRF trusted origins, N+1 query storms) | The failing layer is still unknown (error-triage); the generic reproduce/bisect procedure (debug-from-raw-logs); Node.js (nodejs); Java/Spring (java-spring-stack) |
| [response-self-review](skills/response-self-review/SKILL.md) | A draft asserts a result not seen in tool output this turn ("tests pass", a count, "updated X"), contains a code/file change, or answers a multi-part or format-constrained request | One-line factual replies; trimming length (token-optimizer); validating a prompt for another model (structured-prompting) |
| [structured-prompting](skills/structured-prompting/SKILL.md) | The user asks to write, review, or fix a prompt another model will run (system prompt, template, subagent brief, tool description, CLAUDE.md block), or a prompt-driven output is wrong in a repeatable way | The task is to answer/do the thing yourself rather than write a prompt for it; shaping your own reply's length (token-optimizer) |
| [token-optimizer](skills/token-optimizer/SKILL.md) | The user wants brevity or lower cost, or a reply is about to include >20 lines of code/file/tool output already in context, or would exceed ~150 lines | Tutorial-style answers; self-contained hand-over documents (bug-report-writing); what to *read* (context-hygiene) |

## How auto-loading works

Three invariants make every skill available in every new Claude instance with no manual step:

- **A. Link, don't copy.** `~/.claude/skills` is a junction (Windows) or symlink (POSIX) to this repo's `skills/` folder. A pushed and pulled skill is live in the next session; nothing is copied, so nothing drifts. `install.ps1` / `install.sh` create the link, are idempotent, back up any pre-existing real `~/.claude/skills` directory to `~/.claude/skills.bak-<n>`, adopt stray skill folders into the repo, and never delete user data.
- **B. One always-on index, never a glob.** `skills/INDEX.md` (one row per skill: fires when | does not fire when) is imported by exactly one line in `~/.claude/CLAUDE.md`: `@~/.claude/skills/INDEX.md`. The installers add it if missing and remove the old `@~/.claude/skills/*/SKILL.md` line — glob imports do not expand, and inlining every skill body would cost ~25k tokens per prompt. The index stays under 60 lines.
- **C. Bodies stay lazy.** A `SKILL.md` body is read only when its row matches the task. No per-skill imports in `CLAUDE.md`, no skill content moved into `CLAUDE.md`.

Set-up on a new machine: clone, then `powershell -ExecutionPolicy Bypass -File .\install.ps1` (Windows) or `sh ./install.sh` (macOS/Linux).

## How this repo is maintained

A daily scheduled Claude routine ("Daily AI skills repo update") pulls `main`, verifies the three invariants, writes the next unchecked skill from `ROADMAP.md`, refines the existing skill with the oldest last commit, runs a conflict check across all descriptions, regenerates `INDEX.md`, and pushes two commits (new skill; refinement). Manual contributions are welcome and follow the same conventions. Merges of overlapping skills are recorded in the *Merges* section below.

## Conventions

- One concern per skill; if two skills would fire on the same input, tighten the boundary or merge them (merge when > ~70% of the trigger surface overlaps).
- Every `description` states the trigger concretely and ends with a "Do not use when …" clause naming the sibling skill that owns the adjacent case. `scripts/gen-index.py` refuses to build without it.
- Adjacent skills name each other and the hand-off condition (triage → deep debug, read strategy → reply density).
- Instructions are imperative checklists with 1–2 short worked examples, not essays. Each skill carries at least three hard artifacts: exact commands with flags, a decision table, numeric thresholds, or a named failure mode with its observable tell.
- Keep `SKILL.md` under 150 lines; move long detail into `skills/<name>/references/`.
- Deleting weak content counts as an improvement; a skill that only restates default good behaviour is removed, not polished.

## Merges

None yet.
