---
name: debug-from-raw-logs
description: Diagnose a failure from evidence instead of guesswork. Use when a user reports a bug, crash, failing or flaky test, or "it doesn't work" in a known layer (code, data, or a pinned config/env difference) and a fix would otherwise be proposed from the description alone — obtain the raw logs and stack trace, reproduce, bisect to the smallest failing case, then test hypotheses. Do not use while the failing layer (network/auth/config/code/data) is still unknown — run error-triage first — nor for feature requests or errors whose exact cause is already printed and unambiguous (e.g. a missing import).
---

# Debug From Raw Logs

Treat every bug as a claim to be verified. Fixes proposed before seeing the raw error are guesses; most are wrong and cost the user a round trip. Work through the steps in order and skip none unless the evidence already covers it.

Entry condition: the layer is known (error-triage has pinned it, or the trace makes it obvious). If a `502`, `403`, or "works on their machine" report arrives with no layer, hand off to `error-triage` and come back with its one-line verdict.

## 1. Get the raw evidence first

- Ask for, or fetch yourself, the **unedited** output: the full stack trace, surrounding log lines (at least 20 before the error), exit code, and the exact command that produced it. Paraphrases ("it throws a null error") are not evidence.
- Turn verbosity up before re-running: `--verbose`, `--debug`, `DEBUG=*`, `LOG_LEVEL=debug`, `set -x` for shell, `pytest -vv --tb=long`, `npm run ... --loglevel verbose`. Capture stderr as well as stdout (`2>&1 | tee run.log`).
- Record the environment alongside the log: OS, runtime version, package versions, branch/commit, config flags, whether it is local or CI. Many bugs are "works on my machine" bugs.
- If the log is huge, do not skim it: `grep -n -m1 -E 'ERROR|Traceback|Exception|panic|FATAL' run.log` finds the first error; then `sed -n '<line-20>,<line+40>p' run.log` for its context. The first error is usually the cause and later ones are fallout.

## 2. Read the stack trace properly

- Find the **innermost frame in your own code** (not in a library or the runtime). That is where to look first; library frames tell you how the bad value was used, not where it came from.
- Read the exception type and message literally. `KeyError: 'id'` means the key is absent, not that the value is null.
- Note `Caused by` / chained exceptions: the last one in the chain is the root; the first is the symptom.
- Check line numbers against the code actually deployed (same commit?). Mismatched lines mean stale builds or wrong environment.

## 3. Reproduce before changing anything

- Run the failing command yourself with the same inputs. If you cannot, ask for the minimal input that triggers it.
- Measure determinism, do not assume it: `for i in $(seq 10); do <cmd> >/dev/null 2>&1 || echo FAIL; done | grep -c FAIL`. Read the rate:

| Fails | Points at | Next check |
| --- | --- | --- |
| 10/10 | logic or data | bisect the input (step 4) |
| 2–8/10 | race, ordering, shared state | run the test alone: `pytest tests/x.py::t -p no:randomly`; passes alone ⇒ test pollution, find the polluter with `pytest --lf -x` after `-p randomly --randomly-seed=<failing seed>` |
| ≤ 1/10 | timing, network, resource limits | re-run under load (`stress-ng` / parallel `-n 4`) and with `--timeout` doubled; rate changes ⇒ timing |
| 0/10 locally, fails in CI | environment | diff `env`, runtime version, and lockfile between the two; do not touch code yet |
- Write down the exact repro command. A bug you cannot reproduce is a bug you cannot verify as fixed.

## 4. Bisect to the smallest failing case

- **Input bisection:** halve the input (rows, request body, config file) until removing anything more makes the failure disappear.
- **Code bisection:** `git bisect start; git bisect bad HEAD; git bisect good <last-known-good>` then `git bisect run <repro-command>`. The command must exit 0 for good, 1–127 for bad, and 125 to skip an unbuildable commit; `git bisect log > bisect.log` before `git bisect reset`. Ten commits cost ~4 runs, a thousand cost ~10.
- **Environment bisection:** toggle one variable at a time (dependency version, env var, feature flag, OS). Change one thing per run; two changes per run tell you nothing.
- Stop when the remaining difference between passing and failing is one thing.

## 5. Form hypotheses from the evidence, then test them

- State each hypothesis as a falsifiable sentence: "The request fails because `config.timeout` is read as the string `"30"` and compared to an int."
- For each hypothesis, name the single observation that would confirm or kill it (add a log line, print the type, inspect the variable in a debugger, curl the endpoint directly). Run that check before writing a fix.
- Rank hypotheses by how much of the evidence they explain. Discard any that contradict even one log line.
- Beware of anchoring on the most recent change; it is a strong prior, not proof. Bisection (step 4) settles it.

## 6. Fix, verify, and close the loop

- Apply the smallest change that addresses the root cause, not the symptom (do not wrap the failing line in `try/except` to make the trace go away).
- Re-run the exact repro from step 3; it must now pass. Re-run the broader test suite to catch regressions.
- Add a regression test that would have failed before the fix when the codebase has tests.
- Report back with: root cause in one sentence, the evidence that proved it, the change made, and how it was verified.

## Anti-patterns to refuse

- Declaring a fix from a run that passed once when the failure rate was below 10/10: re-run the loop from step 3 and require 0 failures in 10.
- Deleting or suppressing the error (`|| true`, `catch (e) {}`, `@ts-ignore`, widening a timeout) and calling it fixed.

## Example

**Report:** "The nightly import job fails sometimes."

**Wrong:** "Probably a timeout — increase `IMPORT_TIMEOUT` to 600."

**Right:**
1. Pull the last 5 job logs; 2 of 5 failed, both with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 at position 1042` in `importer/parse.py:88`, innermost own-code frame.
2. Repro: `python -m importer --file failed_2026-09-22.csv` fails every time; the passing nights used files with ASCII-only vendor names.
3. Bisect the CSV to one row containing `Café`. Hypothesis: the file is Latin-1, the reader assumes UTF-8. Check: `file failed.csv` → `ISO-8859 text`. Confirmed.
4. Fix: detect encoding (or open with `encoding="latin-1"` per the vendor contract); add a test with a Latin-1 row; re-run all 5 files — all pass.
