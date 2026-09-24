# ai — reusable Claude skills

A library of small, focused skills for Claude. Each skill is a folder containing a `SKILL.md` with YAML frontmatter (`name`, `description`) followed by imperative, checklist-style instructions that Claude follows when the skill is triggered.

## Layout

```
skills/<name>/SKILL.md     one skill per folder; optional references/ for long detail
ROADMAP.md                 ordered checklist of skills still to be written
README.md                  this file
```

## Skills

| Name | Purpose |
| --- | --- |
| [token-optimizer](skills/token-optimizer/SKILL.md) | High-density, low-token responses; context reuse and proactive token-reduction suggestions |
| [response-self-review](skills/response-self-review/SKILL.md) | Check a draft reply against the request for correctness, completeness, assumptions, and tone before sending |
| [debug-from-raw-logs](skills/debug-from-raw-logs/SKILL.md) | Get raw logs and stack traces first, reproduce, bisect, and test hypotheses from evidence before fixing |

## How this repo is maintained

A daily scheduled Claude routine ("Daily AI skills repo update") pulls `main`, writes the next unchecked skill from `ROADMAP.md`, refines the existing skill with the oldest last commit, and pushes two commits (new skill; refinement). Manual contributions are welcome and follow the same conventions.

## Conventions

- One concern per skill; if a skill grows two purposes, split it.
- Frontmatter `description` states specifically *when* the skill should trigger.
- Instructions are imperative checklists with 1–2 short examples, not essays.
- Keep `SKILL.md` under 150 lines; move long detail into `skills/<name>/references/`.
