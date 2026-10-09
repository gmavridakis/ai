# Roadmap

Ordered checklist. The daily maintenance routine takes the first unchecked item under *Skills to write* each run; the *Migration* section is worked by hand, one step at a time, and needs the evaluation harness first.

## Done

- [x] response-self-review: evaluate a draft reply against the request before sending (correctness, completeness, assumptions, tone)
- [x] debug-from-raw-logs: get raw debug logs/stack traces first, reproduce, bisect, form hypotheses from evidence
- [x] error-triage: classify errors by layer (network/auth/config/code/data) and pick the fastest diagnostic
- [x] context-hygiene: keep the context window lean: what to read, what to summarize, when to compact
- [x] structured-prompting: clear prompts with examples, constraints, output format
- [x] bug-report-writing: minimal repro, expected vs actual, environment, logs
- [x] java-spring-stack: Java / Java EE (Spring Boot, Spring, Hibernate & JPA, JAX-RS & JAX-WS) idioms, conventions, and common pitfalls
- [x] nodejs: Node.js idioms, conventions, and common pitfalls
- [x] python-django: Python (Django) idioms, conventions, and common pitfalls
- [x] angular: Angular idioms, conventions, and common pitfalls
- [x] Conventions pass (2026-10-01): all skills rewritten to `docs/conventions.md`; linter, repo `CLAUDE.md`, ADR 0001, CHANGELOG added

## Skills to write (daily routine, in order)

- [x] flutter-dart: Flutter & Dart idioms, conventions, and common pitfalls (2026-10-02)
- [x] react: React idioms, conventions, and common pitfalls (2026-10-06)
- [x] react-native: React Native idioms, conventions, and common pitfalls (2026-10-07)
- [x] api-debugging: curl reproduction, headers, status codes, request IDs (2026-10-08)
- [x] log-instrumentation: where and how to add useful logging without noise (2026-10-09)
- [ ] performance-profiling: measure before optimizing; timing, flame graphs, N+1 detection
- [ ] dependency-troubleshooting: version conflicts, lockfiles, clean installs
- [ ] safe-refactoring: small verifiable steps, behavior-preserving, diff discipline
- [ ] documentation-writing: README/ADR/runbook structure people actually read
- [ ] estimation-and-scoping: break work down, identify unknowns, give ranges
- [ ] incident-response: triage, communicate, mitigate, root-cause, postmortem
- [ ] security-basics: secrets handling, input validation, least privilege, dependency audit
- [ ] data-validation: schema checks, edge cases, null/empty/unicode handling

## Migration from mattpocock/skills (phase 2, by hand)

Prerequisite, before the first item: an evaluation harness that runs a skill against recorded cases on this machine and grades the `**Done when**` states, so every migrated or refined skill has a pass rate before it is committed.

- [x] evaluation harness: `evals/` (cases per skill with deterministic checks and one judge line per Done-when, run.py / grade.py / report.py around `claude -p`, results committed); 15 cases written, smoke-tested in the sandbox
- [ ] baseline: `python evals/run.py --all` on the user's machine, results committed under `evals/results/`, pass rates recorded in CHANGELOG
- [ ] requirements-clarification ← `grilling`: the frontier-by-rounds interview, numbered questions with a recommended answer, facts are the agent's job and decisions the user's
- [ ] code-review-checklist ← `code-review`: two-axis review (standards + spec) in parallel subagents, Fowler smell baseline, aggregated without re-ranking
- [ ] test-first-fixes ← `tdd` merged with debug-from-raw-logs §3: red before green, one seam per cycle, the failure-rate table
- [ ] debug-from-raw-logs ← `diagnosing-bugs`: fold in the ten ways to build a feedback loop and the "tight loop" tightening pass
- [ ] git-workflow-discipline ← `pr`: PR body template (summary as the smallest visual, before/after evidence, one-way or two-way door, blast radius) plus atomic-commit rules
- [ ] handoff ← `handoff`: compact the conversation into a document another session continues from (user-invoked)
- [ ] retro ← `retro`: after a session, propose environment improvements, most severe first (user-invoked)

Each item: adapt to `docs/conventions.md` and this repo's stacks, keep a `metadata.credits` block, run the harness, record the pass rate in `CHANGELOG.md`.

## Dropped

- code-review-checklist, test-first-fixes, git-workflow-discipline, requirements-clarification as routine items: they move to the migration list above, where a field-tested original exists.
