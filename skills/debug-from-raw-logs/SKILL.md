---
name: debug-from-raw-logs
description: Diagnose a failure from evidence instead of guesswork. Use when a user reports a bug, crash, failing test, or "it doesn't work" and you are tempted to propose a fix from the description alone — first obtain the raw logs and stack trace, reproduce the failure, bisect to the smallest failing configuration, then form and test hypotheses. Do not use for feature requests or for errors whose exact cause is already printed and unambiguous (e.g. a missing import).
---

# Debug From Raw Logs

Treat every bug as a claim to be verified. Fixes proposed before seeing the raw error are guesses; most are wrong and cost the user a round trip. Work through the steps in order and skip none unless the evidence already covers it.

## 1. Get the raw evidence first

- Ask for, or fetch yourself, the **unedited** output: the full stack trace, surrounding log lines (at least 20 before the error), exit code, and the exact command that produced it. Paraphrases ("it throws a null error") are not evidence.
- Turn verbosity up before re-running: `--verbose`, `--debug`, `DEBUG=*`, `LOG_LEVEL=debug`, `set -x` for shell, `pytest -vv --tb=long`, `npm run ... --loglevel verbose`. Capture stderr as well as stdout (`2>&1 | tee run.log`).
- Record the environment alongside the log: OS, runtime version, package versions, branch/commit, config flags, whether it is local or CI. Many bugs are "works on my machine" bugs.
- If the log is huge, do not skim it. Grep for the first `ERROR`, `Traceback`, `Exception`, `panic`, `FATAL`, or non-zero exit; the first error is usually the cause and later ones are fallout.

## 2. Read the stack trace properly

- Find the **innermost frame in your own code** (not in a library or the runtime). That is where to look first; library frames tell you how the bad value was used, not where it came from.
- Read the exception type and message literally. `KeyError: 'id'` means the key is absent, not that the value is null.
- Note `Caused by` / chained exceptions: the last one in the chain is the root; the first is the symptom.
- Check line numbers against the code actually deployed (same commit?). Mismatched lines mean stale builds or wrong environment.

## 3. Reproduce before changing anything

- Run the failing command yourself with the same inputs. If you cannot, ask for the minimal input that triggers it.
- Confirm the failure is deterministic. If it is flaky, run it 5–10 times and note the rate; flaky failures point at timing, ordering, shared state, or environment rather than logic.
- Write down the exact repro command. A bug you cannot reproduce is a bug you cannot verify as fixed.

## 4. Bisect to the smallest failing case

- **Input bisection:** halve the input (rows, request body, config file) until removing anything more makes the failure disappear.
- **Code bisection:** `git bisect start; git bisect bad HEAD; git bisect good <last-known-good>` then `git bisect run <repro-command>` when the repro is scripted.
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

- Proposing a fix from the bug description alone without asking for the trace.
- Editing code while the failure has not yet been reproduced.
- Changing several things at once and declaring victory when the error disappears.
- Deleting or suppressing the error (`|| true`, `catch (e) {}`, `@ts-ignore`) and calling it fixed.

## Example

**Report:** "The nightly import job fails sometimes."

**Wrong:** "Probably a timeout — increase `IMPORT_TIMEOUT` to 600."

**Right:**
1. Pull the last 5 job logs; 2 of 5 failed, both with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 at position 1042` in `importer/parse.py:88`, innermost own-code frame.
2. Repro: `python -m importer --file failed_2026-09-22.csv` fails every time; the passing nights used files with ASCII-only vendor names.
3. Bisect the CSV to one row containing `Café`. Hypothesis: the file is Latin-1, the reader assumes UTF-8. Check: `file failed.csv` → `ISO-8859 text`. Confirmed.
4. Fix: detect encoding (or open with `encoding="latin-1"` per the vendor contract); add a test with a Latin-1 row; re-run all 5 files — all pass.
