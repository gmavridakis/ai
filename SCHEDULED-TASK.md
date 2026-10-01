# Daily AI skills repo update — scheduled task prompt

This file holds the prompt for the Claude desktop scheduled task **"Daily AI skills repo update"**.
Paste everything below the `## Prompt` heading into the task.

## Why this version differs from the original

- **Skills are linked, not copied.** `~/.claude/skills` becomes a junction/symlink to this repo's
  `skills/` folder, so a pushed skill is live in the next Claude instance with no sync step to fail.
- **Only `INDEX.md` is always in context** (~60 lines for 20 skills). Inlining full skill bodies
  would cost roughly 25k tokens on every prompt in every project — more than the skills save.
- **`@~/.claude/skills/*/SKILL.md` is removed.** Glob imports in `CLAUDE.md` do not expand; the
  "always-on" block was a no-op. One explicit import of `INDEX.md` replaces it.
- **`token-optimizer` and `response-self-review` were dropped from the roadmap.** Both already exist
  on disk and are the weakest against the delta test. Step 2 adopts them into the repo; step 5 may
  later cut them down.
- **`debug-from-raw-logs` and `error-triage` are no longer roadmap items** (they exist). Their
  trigger overlap is resolved by step 6's merge threshold rather than a hardcoded merge.
- **Deleting content counts as a refinement.** Without that rule, a daily "improve one skill" loop
  only ever grows files.

---

## Prompt

You maintain the GitHub repository gmavridakis/ai — a library of reusable Claude skills that
auto-load into every Claude instance the user creates. Each skill is a folder under skills/ with a
SKILL.md (YAML frontmatter `name`, `description`, then imperative instructions). Each run: verify the
auto-load wiring, add ONE new skill, refine ONE existing skill, run a conflict check, commit, push,
and report.

### Where the repository is

The repository is a local clone on the user's computer, connected to this session as the folder
C:\Users\gmavr\Desktop\greg-github\ai. In the device shell (device_bash) it is mounted at
$HOME/mnt/ai. Do ALL git and file work there with device_bash (each call is a fresh shell: always
start commands with `cd "$HOME/mnt/ai" &&`). Do not clone the repo anywhere else and do not stage
files into the cloud workspace. Git credentials for pushing are already configured inside the repo
folder by the user; never ask for, print, or copy any token or credential, and never modify the
remote URL or credential settings.

You are running unattended. Do not ask questions; make reasonable choices and state them in the
report. Use web search only briefly for step 4 research.

### The auto-load contract (do not break these)

The user's requirement is that every skill is available in every new Claude instance without manual
setup. That is achieved by three invariants. Check all three every run; repair any that drifted.

A. **Link, don't copy.** `~/.claude/skills` is a junction/symlink to this repo's `skills/` directory,
   so a pushed skill is live in the next instance with no copy step. The repo ships `install.ps1`
   (Windows, uses `New-Item -ItemType Junction`, no admin needed) and `install.sh` (POSIX, `ln -s`).
   Both must be idempotent, must back up any pre-existing real `~/.claude/skills` directory to
   `~/.claude/skills.bak-<n>` before linking, and must never delete user data.

B. **One always-on index, never a glob.** `skills/INDEX.md` is generated from the frontmatter of
   every SKILL.md: one row per skill — `name | when it fires | when it does NOT (which skill owns
   that case instead)`. Keep it under 60 lines total; it is in context on every prompt, so it pays
   rent. The user's `~/.claude/CLAUDE.md` must contain exactly one import line,
   `@~/.claude/skills/INDEX.md`, and must NOT contain `@~/.claude/skills/*/SKILL.md` — glob imports
   do not expand, and inlining full skill bodies would cost ~25k tokens per prompt. If the old glob
   line is present, remove it; if the index import is missing, add it; never duplicate either.

C. **Bodies stay lazy.** A SKILL.md body is loaded when the skill is invoked, not always. Never add
   per-skill `@` imports to CLAUDE.md, and never move skill content into CLAUDE.md.

If `~/.claude` is not reachable from device_bash, do not fail the run: still generate/refresh
INDEX.md and the installers, commit them, and put the exact one-line command the user must run in
the report under "Action needed".

### The value bar (a skill that fails this is not worth loading)

Before committing any new or refined skill, test it against all five. If it fails any, fix it or
pick a different roadmap item — do not ship filler.

1. **Delta test.** Would a competent Claude with no skill loaded behave differently? If the skill
   only restates default good behavior ("be concise", "lead with the answer", "don't guess"), it is
   noise. Reject it.
2. **No duplication of global rules.** Nothing in a skill may restate what is already in the user's
   CLAUDE.md or the Claude Code system prompt. When in doubt, cut it.
3. **Three hard artifacts minimum.** Each skill carries at least three things that cannot be guessed:
   exact commands with flags, a decision table, numeric thresholds, or a named failure mode plus the
   observable tell that identifies it.
4. **Falsifiable instructions.** Every step states an observable action or check. "Think carefully
   about the design" is unfalsifiable; "run the repro 5–10 times and record the failure rate" is not.
5. **Shape.** Under ~150 lines. At least one worked example with realistic output. Deep detail goes
   to `skills/<name>/references/*.md`, not the SKILL.md body.

Prefer procedural skills (a diagnostic sequence, a table, a command set) over style or meta skills
(how to word a reply, how to review your own draft). Procedural skills change behavior; style skills
mostly re-state the system prompt and burn context.

### The conflict rules

1. **One concern per skill.** If two skills would both fire on the same user input, that is a
   conflict.
2. **Every description carries a boundary clause.** The `description` frontmatter must end with
   "Do not use when …", naming the sibling skill that owns the adjacent case.
3. **Explicit handoffs.** Where skills are adjacent (triage → deep debug, write test → fix code),
   each names the other and the condition for handing off.
4. **Merge threshold.** If two skills share more than roughly 70% of their trigger surface, merge
   them into one skill with phases rather than maintaining a boundary nobody can apply. Record the
   merge in README.md.
5. **Never two skills for one workflow stage.** Prefer one skill with a phase 1 / phase 2 structure.

### Steps

1. **Prepare.** `cd "$HOME/mnt/ai" && git config user.name Claude && git config user.email
   noreply@anthropic.com && git checkout main && GIT_TERMINAL_PROMPT=0 git pull --ff-only origin
   main`. If the pull fails, report the exact error and stop.

2. **Adopt strays, then scaffold.**
   - If `~/.claude/skills` is reachable and is a real directory (not yet a link) containing SKILL.md
     folders that are absent from the repo, move them into `skills/` first and note it in the report.
     Never let the same skill exist in two places; that is the main source of drift.
   - If `README.md` is missing, create it: purpose, layout (skills/<name>/SKILL.md, INDEX.md,
     ROADMAP.md, install.ps1, install.sh), a Skills table (name | fires when | does not fire when),
     how auto-loading works (the three invariants above), how the repo is maintained (this routine),
     and the conventions (one concern per skill, imperative checklists, <150 lines, boundary clause
     in every description, detail into references/).
   - If `install.ps1` / `install.sh` are missing, create them per invariant A.
   - If `ROADMAP.md` is missing, create it with the checklist below. Skills already present in
     `skills/` are ticked on creation — never write a skill that already exists.

     - [ ] context-hygiene — what to read, what to summarize, when to compact; token budgets per phase
     - [ ] structured-prompting — prompts with examples, constraints, explicit output format
     - [ ] bug-report-writing — minimal repro, expected vs actual, environment, logs
     - [ ] code-review-checklist — security, correctness, tests, readability, performance
     - [ ] test-first-fixes — reproduce with a failing test before changing code
     - [ ] safe-refactoring — small verifiable steps, behavior-preserving, diff discipline
     - [ ] api-debugging — curl reproduction, headers, status codes, request IDs
     - [ ] log-instrumentation — where and how to add useful logging without noise
     - [ ] performance-profiling — measure before optimizing; timing, flame graphs, N+1 detection
     - [ ] dependency-troubleshooting — version conflicts, lockfiles, clean installs
     - [ ] git-workflow-discipline — atomic commits, clear messages, branch hygiene, safe history edits
     - [ ] documentation-writing — README/ADR/runbook structure people actually read
     - [ ] requirements-clarification — spot ambiguity, ask one good question, state assumptions
     - [ ] estimation-and-scoping — break work down, identify unknowns, give ranges
     - [ ] incident-response — triage, communicate, mitigate, root-cause, postmortem
     - [ ] security-basics — secrets handling, input validation, least privilege, dependency audit
     - [ ] data-validation — schema checks, edge cases, null/empty/unicode handling

3. **Verify the auto-load wiring.** Check invariants A, B, C. Repair what drifted: relink if the
   junction is missing or points elsewhere, regenerate INDEX.md from current frontmatter, fix the
   CLAUDE.md import line. Report each repair in one line.

4. **NEW SKILL.** Take the first unchecked ROADMAP item. Research briefly (web search) for current
   practice, exact tool names, and real flags — the goal is the hard artifacts required by value-bar
   item 3, not prose. Write `skills/<name>/SKILL.md`: frontmatter `name` plus a `description` that
   states the trigger concretely and ends with the "Do not use when …" boundary clause; then
   imperative checklist instructions with 1–2 short worked examples. Apply the value bar; if the
   topic cannot clear it, skip to the next roadmap item and say why in the report. Tick the item,
   add the README table row, regenerate INDEX.md. Write files with a heredoc or a short python
   script in device_bash — never re-type a file from truncated tool output. If every roadmap item is
   checked, skip this step and say so.

5. **REFINE.** Among existing skills excluding the new one, pick the oldest by
   `git log -1 --format=%ci -- skills/<name>`. Read it critically against the value bar and the
   conflict rules. Make one focused improvement pass: delete anything that fails the delta test,
   replace vague steps with commands or thresholds, add the missing edge case or example, and
   sharpen the description's trigger and boundary clause. Deleting weak content counts as a
   refinement — a shorter skill that clears the bar beats a longer one that does not. Do not rewrite
   from scratch. Edit in place with sed or a python read-modify-write.

6. **CONFLICT CHECK.** List every skill's trigger surface from its description. Find any pair that
   would both fire on the same plausible user input. Fix by adding or tightening handoff lines, or
   by merging per rule 4. Regenerate INDEX.md so its boundary column matches the frontmatter exactly.
   Apply at most one merge per run; if more overlaps exist, note them for next run.

7. **COMMIT.** Two commits on `main`: first the new skill plus README/ROADMAP/INDEX and any wiring
   repairs; second the refinement plus any conflict fixes. Clear messages, each ending with:
   Co-Authored-By: Claude <noreply@anthropic.com>
   Then `cd "$HOME/mnt/ai" && GIT_TERMINAL_PROMPT=0 git push origin main`. Do not open a pull
   request. If the push is rejected or fails, report the exact error and stop; do not retry or work
   around it, and do not touch credentials or the remote URL. Record each SHA with
   `git rev-parse HEAD` after committing.

### Report (keep it brief)

- Auto-load: OK, or what was repaired; "Action needed: <one command>" if ~/.claude was unreachable
- New skill: name + one line + which hard artifacts it carries + commit link
  (https://github.com/gmavridakis/ai/commit/<sha>)
- Refined skill: name + what changed (including anything deleted) + commit link
- Conflict check: pairs found, what was done, any overlap deferred to next run
- Remaining unchecked roadmap items: count
- Any problem in one line

End with exactly:
---
To stop these updates: open the Claude desktop app → Scheduled tasks → "Daily AI skills repo update" → switch it off or Delete.
