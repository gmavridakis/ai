# ai: reusable Claude skills

A library of small, focused skills that are live in every Claude Code session on this machine. Each skill is a folder under `skills/` containing a `SKILL.md`: YAML frontmatter (`name`, `description`) followed by imperative phases Claude follows when the skill fires. The skills are diagnostic field manuals for a polyglot enterprise stack (Java/Spring, Node, Django, Angular, Flutter): version pinning, symptom → cause → fix tables with verbatim tells, numeric thresholds, worked examples.

## Layout

```
skills/<name>/SKILL.md      one skill per folder; optional references/ for long detail
skills/INDEX.md             generated one-row-per-skill index; the only file always in context
docs/conventions.md         the author guide every skill follows (adapted from mattpocock/skills)
docs/adr/                   decisions about the repo itself
evals/                      evaluation harness: cases per skill, run.py / grade.py / report.py, committed results
scripts/lint-skills.py      enforces the mechanical conventions; exit 1 blocks a commit
scripts/gen-index.py        regenerates INDEX.md from frontmatter
CLAUDE.md                   what any Claude session working in this repo must do before committing
CHANGELOG.md                one line per change, newest first
ROADMAP.md                  ordered checklist of skills still to be written, and the migration plan
SCHEDULED-TASK.md           the prompt of the daily maintenance routine
install.ps1 / install.sh    one-shot wiring for Windows / POSIX (see below)
```

## Skills

The trigger and boundary of each skill are in [`skills/INDEX.md`](skills/INDEX.md), generated from the descriptions; this table only says what each one does.

| Name | What it does |
| --- | --- |
| [angular](skills/angular/SKILL.md) | Angular 17–22 field manual: pin major and change-detection mode, then an NG-code symptom table (NG0100, NG0203, NG0201, NG8001/8002, hydration, signals, zoneless views that stop updating, budgets) |
| [bug-report-writing](skills/bug-report-writing/SKILL.md) | File a bug someone else can run: duplicate check, seven mandatory fields with the commands that produce them, repro thresholds, title formula and body template |
| [context-hygiene](skills/context-hygiene/SKILL.md) | Keep the context window lean: phase budgets, read strategy by file size, caps on every tool result, a snapshot before compaction |
| [debug-from-raw-logs](skills/debug-from-raw-logs/SKILL.md) | Evidence-first debugging of a known-layer bug: unedited trace, a repro that goes red at a measured rate, bisect, falsifiable hypotheses, four-line report |
| [error-triage](skills/error-triage/SKILL.md) | Pin the failing layer (network, auth, config, code, data) with one diagnostic, report a three-line verdict, hand off to the owning skill |
| [flutter-dart](skills/flutter-dart/SKILL.md) | Flutter 3.38–3.47 field manual: pin SDK, state/routing stack, renderer and Android triad, then a symptom table (RenderFlex overflow, unbounded viewport, setState after dispose, context across async gaps, null check, version solving, MissingPluginException, Gradle/AGP, jank, hot reload) |
| [java-spring-stack](skills/java-spring-stack/SKILL.md) | Spring Boot 2/3/4 field manual: pin Boot, Hibernate and namespace, then a symptom table (LazyInitializationException, N+1, @Transactional, javax→jakarta, Hikari, JAX-RS/JAX-WS) |
| [nodejs](skills/nodejs/SKILL.md) | Node 20–26 field manual: pin runtime and module type, then a symptom table (ESM/CJS errors, unhandled rejections, listeners, heap, event loop, ERESOLVE, SIGTERM, streams) |
| [python-django](skills/python-django/SKILL.md) | Django 4.2–6.x field manual: pin Django and Python, then a symptom table (settings, app registry, migrations, async, transactions, N+1, URLs, templates, static, CSRF, hosts) |
| [response-self-review](skills/response-self-review/SKILL.md) | Check a draft's claims against evidence from this session and its coverage against the request before sending |
| [structured-prompting](skills/structured-prompting/SKILL.md) | Write a prompt for another model: section order, checkable rules, a runnable test loop with a pass-rate bar, failure modes with their tells |
| [token-optimizer](skills/token-optimizer/SKILL.md) | Pick the cheapest output form (diff, reference, full file) and report tool output in a fixed 3-line shape without dropping the literals |

## How auto-loading works

Three invariants make every skill available in every new Claude instance with no manual step:

- **A. Link, don't copy.** `~/.claude/skills` is a junction (Windows) or symlink (POSIX) to this repo's `skills/` folder. A pushed and pulled skill is live in the next session; nothing is copied, so nothing drifts. `install.ps1` / `install.sh` create the link, are idempotent, back up any pre-existing real `~/.claude/skills` directory to `~/.claude/skills.bak-<n>`, adopt stray skill folders into the repo, and never delete user data.
- **B. One always-on index, never a glob.** `skills/INDEX.md` (one row per skill: fires when | does not fire when) is imported by exactly one line in `~/.claude/CLAUDE.md`: `@~/.claude/skills/INDEX.md`. The installers add it if missing and remove the old `@~/.claude/skills/*/SKILL.md` line (glob imports do not expand, and inlining every skill body would cost ~25k tokens per prompt). The index stays under 60 lines, and every description under 70 words.
- **C. Bodies stay lazy.** A `SKILL.md` body is read only when its row matches the task. No per-skill imports in `CLAUDE.md`, no skill content moved into `CLAUDE.md`.

Open question (ADR 0001): Claude Code also injects every skill's description from `~/.claude/skills` into the system prompt on its own. If that holds on this machine, the `INDEX.md` import duplicates it and should be dropped from the installers. Verify with `/context` in a fresh session.

Set-up on a new machine: clone, then `powershell -ExecutionPolicy Bypass -File .\install.ps1` (Windows) or `sh ./install.sh` (macOS/Linux).

## How a skill is tested

`evals/` runs every skill against recorded cases with the real `claude` CLI on this machine, grades deterministic checks plus one judge line per phase (`**Done when**`), and keeps the pass rates in the repo. `python evals/run.py --skill <name>` before and after a change; `--config both` adds a without-skill baseline. See [`evals/README.md`](evals/README.md).

## How this repo is maintained

A daily scheduled Claude routine ("Daily AI skills repo update", prompt in `SCHEDULED-TASK.md`) pulls `main`, verifies the three invariants, writes the next unchecked skill from `ROADMAP.md`, refines the existing skill with the oldest last commit, runs a conflict check across all descriptions, runs `scripts/lint-skills.py`, regenerates `INDEX.md`, appends to `CHANGELOG.md`, and pushes two commits (new skill; refinement). A manual session in the repo follows the same rules via `CLAUDE.md`. Merges of overlapping skills are recorded under *Merges* below; decisions about the repo are ADRs under `docs/adr/`.

## Conventions

The full author guide is [`docs/conventions.md`](docs/conventions.md). The short form:

- The description is a pointer: at most 70 words, trigger first, verbatim tells, and a `Do not use …` boundary naming the sibling that owns the adjacent case.
- The body is numbered phases, each ending in a `**Done when**` line that states an observable state, then unnumbered reference, then an example. At most 150 lines; detail goes to `references/`.
- At least three hard artifacts (exact commands, a decision table, thresholds, a named failure mode with its tell), and nothing a competent agent already does by default.
- Hand-offs are operative: `Call the Skill tool with "<name>"`, with the condition, in both directions between adjacent skills.
- Output shapes are shown as literal templates. One leading word per skill. No em-dashes.
- Borrowed skills keep a `metadata.credits` block; see `docs/conventions.md` §10.
- `scripts/lint-skills.py` must exit 0 before any commit that touches a `SKILL.md`.

## Credits

The conventions adapt the author's guide of [mattpocock/skills](https://github.com/mattpocock/skills) (`writing-for-agents`, MIT). Individual skills adapted from there carry their own credits block.

## Merges

None yet.
