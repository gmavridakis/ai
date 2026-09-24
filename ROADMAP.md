# Roadmap

Ordered checklist of skills to add. The daily maintenance routine takes the first unchecked item each run.

- [x] response-self-review — evaluate a draft reply against the request before sending (correctness, completeness, assumptions, tone)
- [x] debug-from-raw-logs — get raw debug logs/stack traces first, reproduce, bisect, form hypotheses from evidence
- [ ] error-triage — classify errors by layer (network/auth/config/code/data) and pick the fastest diagnostic
- [ ] context-hygiene — keep the context window lean: what to read, what to summarize, when to compact
- [ ] structured-prompting — clear prompts with examples, constraints, output format
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
