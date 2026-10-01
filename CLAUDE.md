This repo is a library of Claude Code skills that auto-load into every session on this machine. One skill per folder under `skills/<name>/SKILL.md`; `skills/INDEX.md` is generated; `docs/conventions.md` is the author guide every skill must follow.

Invariants (details in `README.md`, "How auto-loading works"):

- `~/.claude/skills` is a junction or symlink to this repo's `skills/` folder (`install.ps1` / `install.sh`). Skills are linked, never copied.
- `skills/INDEX.md` is generated from frontmatter by `scripts/gen-index.py` and imported by exactly one line in `~/.claude/CLAUDE.md`. Never add per-skill imports and never move skill content into a `CLAUDE.md`.
- A skill body loads only when the skill fires.

Before committing any change to a `SKILL.md`:

1. Follow `docs/conventions.md` (description at most 70 words with a `Do not use` boundary, a `**Done when**` line per numbered phase, operative `Call the Skill tool with "<name>"` hand-offs, an `## Example`, at most 150 lines, no em-dashes).
2. Run `python3 scripts/lint-skills.py` and fix every error.
3. Run `python3 scripts/gen-index.py`.
4. Update the `README.md` skills table, tick `ROADMAP.md`, add a `CHANGELOG.md` line.

A skill adapted from another repo carries a `metadata.credits` block (see `docs/conventions.md` §10). Decisions about the repo itself are recorded in `docs/adr/`.

No em-dashes anywhere in this repo's prose: rewrite the sentence with a colon, comma, parentheses, or a conjunction.

The unattended daily routine that maintains this repo is described in `SCHEDULED-TASK.md`; a manual session follows the same rules.
