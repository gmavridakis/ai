---
name: context-hygiene
description: Control what enters the context window and when to compact it. Use at the start of any task that touches more than ~5 files or any file over 200 lines, whenever a tool result is longer than 100 lines, before running tests/builds/log scans, and whenever the session is past ~60% of its auto-compact window (check with /context). Do not use for the wording or length of the reply itself — token-optimizer owns output density.
---

# Context Hygiene

Context is a budget, not a scratchpad. Every line read stays in every later request until compaction, so decide *how* to read before reading, cap every tool result, and snapshot state before the window fills.

## 1. Measure before you start (and every ~20 turns)

- Run `/context`. It lists what occupies the window (system prompt, tools, MCP, memory files, messages) and the current total against the auto-compact window.
- Defaults: 1M-window models compact at ~967K tokens; 200K models at the 200K boundary. `/autocompact 500k` (or `CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000`, which overrides everything) lowers it; `/autocompact auto` restores the tuned value.
- Phase budgets, as a share of the auto-compact window. Exceeding a budget means switch to grep/ranges/subagents, not "read faster":

| Phase | Budget | Typical overspend |
| --- | --- | --- |
| Orientation (find the code) | ≤ 10% | reading whole modules to "understand the structure" |
| Implementation | ≤ 40% | re-reading files after each edit |
| Verification (tests, logs) | ≤ 15% | pasting full test output |
| Reserve for compaction + report | ≥ 20% | none; if this is gone, snapshot now |

## 2. Choose the read strategy from size, not curiosity

Check size first: `wc -l <file>` (or `ls -la` for a directory). Then:

| Size | Do | Never |
| --- | --- | --- |
| ≤ 200 lines | read whole file once | read it again unless it changed |
| 200–2,000 lines | `grep -n -E '<symbol\|error>' <file>` → `Read` with `offset`/`limit` ±40 lines around the hit | read whole |
| > 2,000 lines | grep, then ranges; or delegate to a subagent that returns ≤ 30 lines | open in the main context |
| Directory | `ls`, `git ls-files \| head -50`, `tree -L 2` | cat multiple files "to get a feel" |
| Binary / generated / lockfile / minified | never open; `head -c 200` to identify, `file <path>` | read |

- One symbol, one grep: `grep -rn --include='*.ts' 'fetchUser' src/` beats opening three candidate files.
- A file already read this session and not edited since has not changed; do not re-read it. A tool-confirmed edit does not require a verification read either.

## 3. Cap every tool result at the source

- Tests: `pytest -q 2>&1 | tail -40` or `pytest -q --tb=short -x`; `npm test 2>&1 | grep -E 'FAIL|✕|Error' -A5 | head -60`; `go test ./... 2>&1 | grep -v '^ok' | head -60`.
- Logs and builds: `cmd > /tmp/out.log 2>&1; grep -n -m 20 -E 'ERROR|FATAL|Traceback|panic' /tmp/out.log` then `tail -30 /tmp/out.log`. Keep the path; read ranges on demand.
- Data files: `head -20 x.csv; wc -l x.csv`, `jq -c '.[0]' x.json`, `sqlite3 db 'SELECT ... LIMIT 5'`.
- Directory listings: `find . -name '*.py' | wc -l` before `find . -name '*.py'`.
- Anything that would return > 100 lines: run it in a subagent (`Agent` tool / Task) with "return only failures, ≤ 30 lines" in the prompt. The verbose output stays in the subagent's window.
- Hard rule: no single tool result over 200 lines in the main context. If one lands, do not paste it back; summarize it in ≤ 5 lines and move on.

## 4. Snapshot before the window fills

At 60% of the auto-compact window, or at the end of a task phase, write a snapshot to a file (`NOTES.md` in the working directory, or the task list) before compacting. Auto-compaction summarizes on its own, but it does not know what matters. The snapshot must contain:

1. Goal in one sentence and the acceptance check (the exact command that proves done).
2. Decisions made and why (one line each); rejected options with the reason.
3. Files touched, with the function names changed; files read but not yet needed.
4. Open questions and the next three concrete steps.
5. Exact repro/test commands and where their output lives (`/tmp/out.log`).

Then compact with focus: `/compact focus on NOTES.md, the failing test, and the diff`. Between unrelated tasks use `/clear` (free) — `/compact` itself is a large request because it reads the whole conversation. `/rename` first so `/resume` can find the session.

## 5. Failure modes and their tells

| Failure mode | Observable tell | Fix |
| --- | --- | --- |
| Context rot | you ask the user something already answered, or re-read a file read < 20 turns ago | grep the conversation state from the snapshot; stop re-reading |
| Log flood | one tool result scrolls > 200 lines; the next reply quotes it | redirect to file, grep -m, `tail -40` |
| Compaction amnesia | first action after compaction is re-reading 3+ files | snapshot was missing or incomplete; write it now, compact again with focus |
| Orientation spiral | > 10% of the window spent and no file has been edited | stop reading; state the plan from what is known; ask one question if needed |
| MCP bloat | `/context` shows tools/MCP > 15% of the window | `/mcp` to disable unused servers; prefer CLIs (`gh`, `aws`) |

## Example

Task: "Fix the flaky `test_import_latin1` in a 40k-line Django repo."

1. `/context` → 38K of 967K used. Budget: orientation ≤ 97K.
2. `grep -rn 'test_import_latin1' tests/` → one hit. `Read tests/test_import.py` offset 210 limit 60 (file is 1,400 lines). `grep -n 'def import_csv' -r importer/` → `importer/parse.py:71`; read 60–130.
3. `pytest tests/test_import.py::test_import_latin1 -q --tb=short -x 2>&1 | tail -30` → 18 lines, `UnicodeDecodeError` at `parse.py:88`.
4. Edit `parse.py:88`; re-run the same command (not the whole suite). Passes. Do not re-read `parse.py`.
5. `/context` → 61K. Below budget; no compaction. Write two-line snapshot in NOTES.md anyway (fix + command), then run the full suite in a subagent: "run `pytest -q`, return failures only, ≤ 30 lines."

Total main-context reads: 2 ranges, 1 grep, 2 test tails. Never opened the 1,400-line test file whole.
