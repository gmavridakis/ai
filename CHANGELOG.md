# Changelog

One line per change, newest first. The daily routine appends here; a manual session does the same.

## 2026-10-01

- Routine prompt: step 4 writes an eval case for each new skill; the stored scheduled task was updated to the new prompt.
- Add the evaluation harness `evals/`: 15 cases (one per skill plus four routing cases) with fixtures, deterministic checks and judge lines per `**Done when**`; `run.py` (claude -p, with/without skill, `--ref` for an older version), `grade.py`, `report.py` (summary.md + skill-creator-compatible benchmark.json). Smoke runs in the sandbox: routing cases pass; error-triage did not fire on its own case in 1 of 1 runs (baseline pending on the user's machine).
- Rewrite all 11 skills to `docs/conventions.md`: descriptions cut to at most 70 words (average was 130), a `**Done when**` state per phase, operative `Call the Skill tool with "<name>"` hand-offs in both directions, literal templates for the verdict (error-triage), the report (debug-from-raw-logs), the tool-output shape (token-optimizer); reference sections unnumbered; em-dashes removed. Tables, commands, thresholds and examples unchanged. `INDEX.md` shrinks from 1,492 to 820 words.
- `README.md`: skills table is now name + purpose (triggers live only in `INDEX.md`); conventions, credits and the INDEX-duplication open question added. `ROADMAP.md`: split into *Skills to write* (routine) and *Migration from mattpocock/skills* (by hand, harness first). `SCHEDULED-TASK.md`: prompt points at the conventions and the linter; must be re-pasted into the desktop task.
- Adopt the mattpocock/skills prompt-writing conventions repo-wide: `docs/conventions.md`, root `CLAUDE.md`, `scripts/lint-skills.py`, this changelog, ADR 0001.
- Add angular skill; refine structured-prompting (runnable test harness, example-beats-rule failure mode); nodejs no longer fires on every Angular workspace (daily routine, earlier today).
