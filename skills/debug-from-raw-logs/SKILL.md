---
name: debug-from-raw-logs
description: Diagnose a reported bug from raw evidence: unedited trace, a repro that goes red, bisect, falsifiable hypotheses. Use for a crash, failing or flaky test, or "it doesn't work" in a known layer when the fix would otherwise be guessed. Do not use while the layer is unknown (error-triage first), when a stack table names the tell (java-spring-stack, nodejs, python-django, angular, flutter-dart, react), or the cause is unambiguous.
---

# Debug From Raw Logs

A fix proposed before the raw error is seen is a guess; most guesses are wrong and cost the user a round trip. Work the phases in order; the only phase you may skip is one the evidence already covers.

Entry conditions, checked before phase 1:

- The layer is unknown (a `502`, `403`, or "works on their machine" report with no layer): Call the Skill tool with "error-triage" and return with its verdict.
- The first error line may be a stack tell. Look it up in the stack's symptom table before bisecting: in a Spring project Call the Skill tool with "java-spring-stack"; in a Node project Call the Skill tool with "nodejs"; in a Django project Call the Skill tool with "python-django"; in an Angular workspace Call the Skill tool with "angular"; in a Flutter app Call the Skill tool with "flutter-dart"; in a React or Next.js app Call the Skill tool with "react". Only an unmatched tell continues here.

## 1. Get the raw evidence first

- Ask for, or fetch yourself, the **unedited** output: the full stack trace, at least 20 log lines before the error, the exit code, and the exact command that produced it. Paraphrases ("it throws a null error") are not evidence.
- Turn verbosity up before re-running: `--verbose`, `--debug`, `DEBUG=*`, `LOG_LEVEL=debug`, `set -x` for shell, `pytest -vv --tb=long`, `npm run ... --loglevel verbose`. Capture stderr as well as stdout (`2>&1 | tee run.log`).
- Record the environment alongside the log: OS, runtime version, package versions, branch/commit, config flags, local or CI. Many bugs are "works on my machine" bugs.
- A huge log is searched, not skimmed: `grep -n -m1 -E 'ERROR|Traceback|Exception|panic|FATAL' run.log` finds the first error; `sed -n '<line-20>,<line+40>p' run.log` gives its context. The first error is usually the cause and later ones are fallout.

**Done when** the unedited trace, its 20 lines of context, the exit code, the exact command, and the environment are in front of you, pasted rather than described.

## 2. Read the stack trace properly

- Find the **innermost frame in your own code** (not in a library or the runtime). That is where to look first; library frames tell you how the bad value was used, not where it came from.
- Read the exception type and message literally. `KeyError: 'id'` means the key is absent, not that the value is null.
- Follow `Caused by` / chained exceptions: the last one in the chain is the root; the first is the symptom.
- Check line numbers against the code actually deployed (same commit?). Mismatched lines mean a stale build or the wrong environment.

**Done when** you can name the innermost own-code frame as `file:line`, the root exception at the end of the `Caused by` chain, and the commit the line numbers belong to.

## 3. Build a repro that goes red

- Run the failing command yourself with the same inputs. If you cannot, ask for the minimal input that triggers it.
- Measure determinism instead of assuming it: `for i in $(seq 10); do <cmd> >/dev/null 2>&1 || echo FAIL; done | grep -c FAIL`. Read the rate:

| Fails | Points at | Next check |
| --- | --- | --- |
| 10/10 | logic or data | bisect the input (step 4) |
| 2–8/10 | race, ordering, shared state | run the test alone: `pytest tests/x.py::t -p no:randomly`; passes alone ⇒ test pollution, find the polluter with `pytest --lf -x` after `-p randomly --randomly-seed=<failing seed>` |
| ≤ 1/10 | timing, network, resource limits | re-run under load (`stress-ng` / parallel `-n 4`) and with `--timeout` doubled; rate changes ⇒ timing |
| 0/10 locally, fails in CI | environment | diff `env`, runtime version, and lockfile between the two; leave the code alone |

- Write down the exact repro command: it is the *red* command every later phase runs.

**Done when** one command is written down that you have run at least once, goes red at a recorded rate (`n/10`), and prints the user's first error line. No red command, no step 4: a bug you cannot reproduce is a bug you cannot verify as fixed.

## 4. Bisect to the smallest failing case

- **Input bisection:** halve the input (rows, request body, config file) until removing anything more makes the failure disappear.
- **Code bisection:** `git bisect start; git bisect bad HEAD; git bisect good <last-known-good>` then `git bisect run <red command>`. The command must exit 0 for good, 1–127 for bad, and 125 to skip an unbuildable commit; `git bisect log > bisect.log` before `git bisect reset`. Ten commits cost ~4 runs, a thousand cost ~10.
- **Environment bisection:** toggle one variable at a time (dependency version, env var, feature flag, OS). Two changes per run tell you nothing.

**Done when** exactly one difference separates the passing and failing runs (one input, one commit, or one environment variable) and the red command still goes red with everything else removed.

## 5. Form hypotheses from the evidence, then test them

- State each hypothesis as a falsifiable sentence: "The request fails because `config.timeout` is read as the string `"30"` and compared to an int."
- For each hypothesis, name the single observation that would confirm or kill it (add a log line, print the type, inspect the variable in a debugger, curl the endpoint directly). Run that check before writing a fix.
- Rank hypotheses by how much of the evidence they explain. Discard any that contradict even one log line.
- The most recent change is a strong prior, not proof. Bisection (step 4) settles it.

**Done when** every hypothesis is one falsifiable sentence with its single check, every check has been run, and exactly one hypothesis survives.

## 6. Fix, verify, and close the loop

- The surviving hypothesis places the root cause inside a third-party package or vendor component (the innermost own-code frame only calls into it): the fix is upstream. Call the Skill tool with "bug-report-writing" with the red command and its `n/10` rate; here, ship only a pinned version or a workaround and name it in *Change*.
- Apply the smallest change that addresses the root cause, not the symptom.
- Re-run the red command; it must now pass. Re-run the broader test suite to catch regressions.
- Add a regression test that would have failed before the fix, wherever the codebase has tests.
- Report in this shape:

```
Root cause: <one sentence>
Evidence: <the log line or check that proved it>
Change: <path:line, what changed>
Verified: <red command> → <result n/10>; <suite command> → <result>; regression test <path or "none: <reason>">
```

**Done when** the red command is green 10/10, the suite is green, a regression test exists or its absence is explained, and the four-line report is in the reply.

## Anti-patterns to refuse

- Declaring a fix from a run that passed once when the failure rate was below 10/10: re-run step 3 and require 0 failures in 10.
- Deleting or suppressing the error (`|| true`, `catch (e) {}`, `@ts-ignore`, widening a timeout) and calling it fixed.

## Example

**Report:** "The nightly import job fails sometimes."

**Wrong:** "Probably a timeout: increase `IMPORT_TIMEOUT` to 600."

**Right:**
1. Pull the last 5 job logs; 2 of 5 failed, both with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 at position 1042` in `importer/parse.py:88`, the innermost own-code frame.
2. Red command: `python -m importer --file failed_2026-09-22.csv` fails 10/10; the passing nights used files with ASCII-only vendor names.
3. Bisect the CSV to one row containing `Café`. Hypothesis: the file is Latin-1, the reader assumes UTF-8. Check: `file failed.csv` → `ISO-8859 text`. Confirmed.
4. Fix: detect the encoding (or open with `encoding="latin-1"` per the vendor contract); add a test with a Latin-1 row; re-run all 5 files: all pass. Report with the four lines.
