---
name: context-hygiene
description: Control what enters the context window and when to compact. Use at the start of a task touching more than 5 files or any file over 200 lines, when a tool result exceeds 100 lines, before tests, builds, or log scans, and past 60% of the auto-compact window (check /context). Do not use for the wording or length of the reply (token-optimizer) or for writing a subagent's brief (structured-prompting).
---

# Context Hygiene

Context is a budget, not a scratchpad. Every line read stays in every later request until compaction, so decide *how* to read before reading, *cap* every tool result, and *snapshot* state before the window fills.

The reply, not the window, is what is too long: Call the Skill tool with "token-optimizer". A brief for a subagent is a prompt for another model: Call the Skill tool with "structured-prompting".

## 1. Measure before you start (and every ~20 turns)

- Run `/context`; write down the total against the auto-compact window and the share taken by tools and MCP.
- Defaults: 1M-window models compact at ~967K tokens; 200K models at the 200K boundary. `/autocompact 500k` (or `CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000`, which overrides everything) lowers it; `/autocompact auto` restores the tuned value.
- Phase budgets, as a share of the auto-compact window. Exceeding a budget means switch to grep, ranges, or subagents, not "read faster":

| Phase | Budget | Typical overspend |
| --- | --- | --- |
| Orientation (find the code) | ≤ 10% | reading whole modules to "understand the structure" |
| Implementation | ≤ 40% | re-reading files after each edit |
| Verification (tests, logs) | ≤ 15% | pasting full test output |
| Reserve for compaction + report | ≥ 20% | none; if this is gone, snapshot now |

**Done when** two numbers are written down: the `/context` total now, and this phase's budget in tokens.

## 2. Choose the read strategy from size, not curiosity

Check size first: `wc -l <file>` (or `ls -la` for a directory). Then:

| Size | Do | Never |
| --- | --- | --- |
| ≤ 200 lines | read whole file once | read it again unless it changed |
| 200–2,000 lines | `grep -n -E '<symbol\|error>' <file>` → `Read` with `offset`/`limit` ±40 lines around the hit | read whole |
| > 2,000 lines | grep, then ranges; or delegate to a subagent that returns ≤ 30 lines | open in the main context |
| Directory | `ls`, `git ls-files \| head -50`, `tree -L 2 -I 'node_modules\|.git\|dist\|build\|target\|.venv'` (without `-I` a JS or Java tree returns thousands of lines) | cat multiple files "to get a feel" |
| Binary / generated / lockfile / minified | never open; `head -c 200` to identify, `file <path>` | read |

- One symbol, one grep: `grep -rn --include='*.ts' 'fetchUser' src/` beats opening three candidate files.

**Done when** every read in this phase was preceded by a size check and used the row's method; no file over 200 lines was opened whole.

## 3. Cap every tool result at the source

- Tests: `pytest -q 2>&1 | tail -40` or `pytest -q --tb=short -x`; `npm test 2>&1 | grep -E 'FAIL|✕|Error' -A5 | head -60`; `go test ./... 2>&1 | grep -v '^ok' | head -60`.
- Logs and builds: `cmd > /tmp/out.log 2>&1; grep -n -m 20 -E 'ERROR|FATAL|Traceback|panic' /tmp/out.log` then `tail -30 /tmp/out.log`. Keep the path; read ranges on demand.
- PowerShell (Windows outside Git Bash, where `head`/`tail`/`grep` do not exist): `cmd *> out.log; Select-String -Path out.log -Pattern 'ERROR|FATAL|Exception' | Select-Object -First 20`; `Get-Content out.log -Tail 30`; `Get-Content x.csv -TotalCount 20`; `(Get-ChildItem -Recurse -Filter *.py).Count`.
- Data files: `head -20 x.csv; wc -l x.csv`, `jq -c '.[0]' x.json`, `sqlite3 db 'SELECT ... LIMIT 5'`.
- Directory listings: `find . -name '*.py' | wc -l` before `find . -name '*.py'`.
- Anything that would return > 100 lines: run it in a subagent (`Agent` tool) with "return only failures, ≤ 30 lines" in the brief. The verbose output stays in the subagent's window.
- Hard cap: no single tool result over 200 lines in the main context. If one lands, summarize it in ≤ 5 lines and move on; the reply never quotes it.

**Done when** no tool result in the main context exceeds 200 lines, and every output longer than that has a file path the reply can point to.

## 4. Snapshot before the window fills

At 60% of the auto-compact window, or at the end of a task phase, write a snapshot to a file (`NOTES.md` in the working directory, or the task list) before compacting. Auto-compaction summarizes on its own, but it does not know what matters. In a repo, keep the file out of the diff: `echo NOTES.md >> .git/info/exclude` (not `.gitignore`, which would be committed). The snapshot carries:

1. Goal in one sentence and the acceptance check (the exact command that proves done).
2. Decisions made and why (one line each); rejected options with the reason.
3. Files touched, with the function names changed; files read but not yet needed.
4. Open questions and the next three concrete steps.
5. Exact repro/test commands and where their output lives (`/tmp/out.log`).

Then compact with focus: `/compact focus on NOTES.md, the failing test, and the diff`. Between unrelated tasks use `/clear` (free); `/compact` itself is a large request because it reads the whole conversation. `/rename` first so `/resume` can find the session.

**Done when** `NOTES.md` holds all five items, `git status --short` does not list it, and either `/compact` ran with a focus line or `/clear` ran between unrelated tasks.

## Failure modes and their tells

| Failure mode | Observable tell | Fix |
| --- | --- | --- |
| Context rot | you ask the user something already answered, or re-read a file read < 20 turns ago | before any `Read`, check `NOTES.md` item 3 (files touched and read); a file listed there with no edit since is answered from the snapshot, not re-opened |
| Log flood | one tool result scrolls > 200 lines; the next reply quotes it | redirect to file, `grep -m`, `tail -40` |
| Compaction amnesia | first action after compaction is re-reading 3+ files | snapshot was missing or incomplete; write it now, compact again with focus |
| Orientation spiral | > 10% of the window spent and no file has been edited | stop reading; state the plan from what is known; ask one question if needed |
| MCP bloat | `/context` shows tools/MCP > 15% of the window | `/mcp` to disable unused servers; prefer CLIs (`gh`, `aws`) |

## Example

Task: "Fix the flaky `test_import_latin1` in a 40k-line Django repo."

1. `/context` → 38K of 967K used. Budget: orientation ≤ 97K.
2. `grep -rn 'test_import_latin1' tests/` → one hit. `Read tests/test_import.py` offset 210 limit 60 (file is 1,400 lines). `grep -n 'def import_csv' -r importer/` → `importer/parse.py:71`; read 60–130.
3. `pytest tests/test_import.py::test_import_latin1 -q --tb=short -x 2>&1 | tail -30` → 18 lines, `UnicodeDecodeError` at `parse.py:88`.
4. Edit `parse.py:88`; re-run the same command (not the whole suite). Passes. `parse.py` is not re-read.
5. `/context` → 61K. Below budget; no compaction. Write the two-line snapshot in `NOTES.md` anyway (fix + command), then run the full suite in a subagent: "run `pytest -q`, return failures only, ≤ 30 lines."

Total main-context reads: 2 ranges, 1 grep, 2 test tails. The 1,400-line test file was never opened whole.
