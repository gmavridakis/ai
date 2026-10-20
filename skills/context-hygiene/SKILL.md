---
name: context-hygiene
description: Control what enters the context window and when to compact. Use at the start of a task touching more than 5 files or any file over 200 lines, when a tool result exceeds 100 lines, before tests, builds, or log scans, and past 60% of the auto-compact window (check /context). Do not use for the wording or length of the reply (token-optimizer) or for writing a subagent's brief (structured-prompting).
---

# Context Hygiene

Context is a budget, not a scratchpad. Every line read stays in every later request until compaction, so decide *how* to read before reading, *cap* every tool result, and *snapshot* state before the window fills.

The reply, not the window, is what is too long: Call the Skill tool with "token-optimizer". A brief for a subagent is a prompt for another model: Call the Skill tool with "structured-prompting".

## 1. Measure before you start (and every ~20 turns)

- Run `/context`; write down the total against the auto-compact window and the share taken by tools and MCP.
- Defaults (Oct 2026): 1M-window models compact at ~967K tokens; 200K models at the 200K boundary. `/autocompact 500k` (100k to 1M, saved per model; `--autocompact 500k` for one launch; `CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000` overrides all three) lowers it; `/autocompact auto` restores the tuned value.
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
- Logs and builds: `cmd > /tmp/out.log 2>&1; grep -n -m 20 -E 'ERROR|FATAL|Traceback|panic' /tmp/out.log` then `tail -30 /tmp/out.log`. Keep the path; read ranges on demand. The cap is on the window, not on the evidence: the file keeps the unedited run, and the first-error range (`sed -n '<line-20>,<line+40>p'`) is what a diagnosis pastes. When that range shows a crash or a failing test in a known layer and the cause is not in the tell itself: Call the Skill tool with "debug-from-raw-logs" with the file path and the range. A log that cannot be narrowed by request ID or parsed with `jq` (text lines, no ID field) is an instrumentation gap: Call the Skill tool with "log-instrumentation" after the current task.
- PowerShell (Windows outside Git Bash, where `head`/`tail`/`grep` do not exist): `cmd *> out.log; Select-String -Path out.log -Pattern 'ERROR|FATAL|Exception' | Select-Object -First 20`; `Get-Content out.log -Tail 30`; `Get-Content x.csv -TotalCount 20`; `(Get-ChildItem -Recurse -Filter *.py).Count`.
- Data files: `head -20 x.csv; wc -l x.csv`, `jq -c '.[0]' x.json`, `sqlite3 db 'SELECT ... LIMIT 5'`.
- Directory listings: `find . -name '*.py' | wc -l` before `find . -name '*.py'`.
- Diffs and history: `git diff --stat` first, then `git diff -- <file>` for one file at a time; `git log --oneline -n 20`, `git show --stat <sha>`. A bare `git diff` or `git log` on a change over 5 files is the most common flood after test output.
- Results with no pipe (built-in and MCP tools): use the tool's own bound before calling. `Read` with `offset`/`limit` (never a bare `Read` on a file over 200 lines), `Grep` with `head_limit` and `-C` instead of `-A 50`, a browser page with `find` or `get_page_text` on one section instead of a full `read_page`, a connector list with its `limit`/`page_size` argument at 20. A tool with no bound (a page dump, a list endpoint with no paging) is called from a subagent, never from the main context.
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

**Done when** `NOTES.md` holds all five items, `git status --short` does not list it, and the window action matches the state: past 60%, `/compact` ran with a focus line; a new unrelated task, `/clear` ran; below 60% and same task, neither ran and the `/context` total is written beside the snapshot.

## Failure modes and their tells

| Failure mode | Observable tell | Fix |
| --- | --- | --- |
| Context rot | you ask the user something already answered, or re-read a file read < 20 turns ago | before any `Read`, check `NOTES.md` item 3 (files touched and read); a file listed there with no edit since is answered from the snapshot, not re-opened |
| Log flood | one tool result scrolls > 200 lines; the next reply quotes it | redirect to file, `grep -m`, `tail -40` |
| Unbounded tool call | a `Read`, `read_page`, or connector list lands at > 200 lines with no `limit`, `head_limit`, or `find` in the call | re-issue the call with its bound (phase 3); if the tool has none, move the call to a subagent |
| Compaction amnesia | first action after compaction is re-reading 3+ files | snapshot was missing or incomplete; write it now, compact again with focus |
| Orientation spiral | > 10% of the window spent and no file has been edited | stop reading; state the plan from what is known; ask one question if needed |
| MCP bloat | `/context` shows tools/MCP > 15% of the window | `/mcp` to disable unused servers; prefer CLIs (`gh`, `aws`) |

## Example

Task: "Fix the flaky `test_import_latin1` in a 40k-line Django repo."

1. `/context` → 38K of 967K used. Budget: orientation ≤ 97K.
2. `grep -rn 'test_import_latin1' tests/` → one hit. `Read tests/test_import.py` offset 210 limit 60 (file is 1,400 lines). `grep -n 'def import_csv' -r importer/` → `importer/parse.py:71`; read 60–130.
3. `pytest tests/test_import.py::test_import_latin1 -q --tb=short -x 2>&1 | tail -30` → 18 lines, `UnicodeDecodeError` at `parse.py:88`.
4. Edit `parse.py:88`; re-run the same command (not the whole suite). Passes. `parse.py` is not re-read.
5. `/context` → 61K. Below 60%, same task: no `/compact`, no `/clear`. Write the two-line snapshot in `NOTES.md` anyway (fix + command, `61K` beside it), then run the full suite in a subagent: "run `pytest -q`, return failures only, ≤ 30 lines."

Total main-context reads: 2 ranges, 1 grep, 2 test tails. The 1,400-line test file was never opened whole.
