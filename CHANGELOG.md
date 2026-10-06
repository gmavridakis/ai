# Changelog

One line per change, newest first. The daily routine appends here; a manual session does the same.

## 2026-10-06

- Conflict check: react versus nodejs both fire on a Next.js package (`package.json` with `react-dom` that also runs in Node); resolved by boundary clauses and operative hand-offs in both directions (nodejs → react for components, hooks, hydration and routes; react → nodejs for ERESOLVE, ERR_REQUIRE_ESM, heap, Node version). java-spring-stack and python-django now hand a React or Flutter front end to react / flutter-dart (closes the overlap deferred on 2026-10-02). No merge. Deferred: none.
- Refine angular: the backend hand-off is now one conditional `Call the Skill tool` line per stack (Spring, Node, Django) plus a React-monorepo hand-off, instead of three names in one sentence; two rows added to the symptom table, `NG0302` (pipe not found in a standalone component, the most common post-migration tell) and `NG0200` (circular DI); NG0302 added to the description's trigger list.
- Add react skill: pin React 18.3 to 19.3 (Oct 2026 table: 19 removals and codemods, 19.2 `useEffectEvent`/`Activity`/React Compiler 1.0, Next.js 16 async request APIs, 19.3 `ViewTransition`/`use(browser())`, Vite 8 compiler wiring), 18-row symptom table with verbatim React, Next.js, eslint and test tells, observation commands (DevTools Profiler, react-scan), worked example; error-triage, debug-from-raw-logs and nodejs route to it (both directions). Eval case `evals/cases/react/` written, to be run on the user's machine.

## 2026-10-02

- Conflict check: bug-report-writing handed off to error-triage and debug-from-raw-logs but neither handed back, so "crash X, write it up for the maintainers" fired both; error-triage (vendor/third-party layer, user wants it reported) and debug-from-raw-logs (§6, root cause inside a dependency) now Call the Skill tool with "bug-report-writing". No merge. Deferred: the four stack skills do not yet route a Flutter frontend to flutter-dart.
- Refine bug-report-writing: phase 1 and phase 4 cover a Jira or vendor-portal tracker (jira-cli search and create commands, 0-match Done when); field 2 gains the Java (`java -version`, `mvn -v`/`./gradlew -v`) and Flutter (`flutter --version --machine`) environment commands.
- Add flutter-dart skill: pin Flutter/Dart (3.38 to 3.47.5, Oct 2026 table with the 3.47 Android triad AGP 9.1.0 / Gradle 9.3.1 / Kotlin 2.4.0 / JDK 17), 18-row symptom table with verbatim framework tells, observation commands, worked example; error-triage and debug-from-raw-logs route to it (both directions). Eval case `evals/cases/flutter-dart/` written, to be run on the user's machine.

## 2026-10-01

- Routine prompt: step 4 writes an eval case for each new skill; the stored scheduled task was updated to the new prompt.
- Add the evaluation harness `evals/`: 15 cases (one per skill plus four routing cases) with fixtures, deterministic checks and judge lines per `**Done when**`; `run.py` (claude -p, with/without skill, `--ref` for an older version), `grade.py`, `report.py` (summary.md + skill-creator-compatible benchmark.json). Smoke runs in the sandbox: routing cases pass; error-triage did not fire on its own case in 1 of 1 runs (baseline pending on the user's machine).
- Rewrite all 11 skills to `docs/conventions.md`: descriptions cut to at most 70 words (average was 130), a `**Done when**` state per phase, operative `Call the Skill tool with "<name>"` hand-offs in both directions, literal templates for the verdict (error-triage), the report (debug-from-raw-logs), the tool-output shape (token-optimizer); reference sections unnumbered; em-dashes removed. Tables, commands, thresholds and examples unchanged. `INDEX.md` shrinks from 1,492 to 820 words.
- `README.md`: skills table is now name + purpose (triggers live only in `INDEX.md`); conventions, credits and the INDEX-duplication open question added. `ROADMAP.md`: split into *Skills to write* (routine) and *Migration from mattpocock/skills* (by hand, harness first). `SCHEDULED-TASK.md`: prompt points at the conventions and the linter; must be re-pasted into the desktop task.
- Adopt the mattpocock/skills prompt-writing conventions repo-wide: `docs/conventions.md`, root `CLAUDE.md`, `scripts/lint-skills.py`, this changelog, ADR 0001.
- Add angular skill; refine structured-prompting (runnable test harness, example-beats-rule failure mode); nodejs no longer fires on every Angular workspace (daily routine, earlier today).
