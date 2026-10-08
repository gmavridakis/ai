---
name: response-self-review
description: Check a finished draft against evidence before sending. Use when the draft asserts a result not seen in tool output this turn ("tests pass", "fixed", a count, a version, "updated the README"), contains a code or file change, or answers a multi-part request or an explicit format or length constraint. Do not use for one-line replies, to trim length (token-optimizer), or to validate a prompt for another model (structured-prompting).
---

# Response Self-Review

Review the draft as a skeptical reader who has only the original request, not your reasoning. Every *claim* in the draft either has *evidence* from this session or is labelled as unverified. Fix what you find, then send; the review itself never appears in the reply.

Trimming length or density is a different job: Call the Skill tool with "token-optimizer". A draft that is a prompt for another model is validated by its test loop instead: Call the Skill tool with "structured-prompting".

Pick the depth from the draft, not from how confident you feel:

| Draft contains | Run phases | Also |
| --- | --- | --- |
| ≤ 5 lines, no artifact, no number | none; send | |
| a number, count, date, or version | 1 | recompute it with a command, not in prose |
| a code change or edited file | 1, 2 | `git diff --stat` must list only files the request named |
| a new file, document, or plan | 1, 2 | map every explicit ask to a line in the draft |

Budget: at most 3 tool calls per review and no re-drafting; fix in place. A check that needs more than that is reported as unverified, with the command the user can run to confirm it. The label has one shape, placed on the line that makes the claim:

```
Unverified: <claim>. Confirm with `<command>`.
```

## 1. Correctness

Classify each claim in the draft as verified (you ran, read, or searched it this session), inferred, or assumed. Every inferred or assumed claim is either verified now with the matching check, or labelled as unverified in the reply.

| Claim in draft | Evidence that counts | Not evidence |
| --- | --- | --- |
| "the code works" / "tests pass" | you ran it this turn and saw exit code 0 | it compiled; it looked right |
| a count, total, or date | output of `wc -l`, `grep -c`, a script, or `date -d` | arithmetic done in prose |
| a flag, path, signature, or version | `--help`, the file, or `pkg --version` shown in this session | memory |
| "I changed X" / "updated three tests" | `git diff --stat` and `git status --short` name exactly those files | your intent |
| a quoted line or error | the line as it appears in the tool output | a paraphrase |
| a number read from a tool result that was cut off (`...`, `[truncated]`, `+N lines`, a `head`/`tail` window) | `wc -l`, `grep -c`, or `jq length` on the file itself | the visible part of the capped output |
| "pushed" / "CI is green" / "deployed" | `git status -sb` showing `ahead 0`, the pipeline URL or run id in tool output | the push command having returned |

Then read the draft once end-to-end for internal contradictions: a summary sentence that disagrees with its own table or list is the most common tell.

**Done when** every claim has a classification, every inferred or assumed claim is either backed by a check run this turn or carries an `Unverified:` line in the reply, and the end-to-end read found no sentence that contradicts another.

## 2. Completeness

- Map every explicit ask (verbs, deliverables, formats, counts, constraints such as "under 150 lines", "as a table", "don't touch X") to the line in the draft that answers it. An unmapped ask is a gap: answer it, or state in one line that it was skipped and why.
- Multi-part requests: count the parts ("and", numbered items, "for each") and count the answers; the numbers must match.
- Length and format constraints are checked with a command, not by eye: `wc -l file`, `head -c 300 file` for the required opening, `python -c "import json;json.load(open('x.json'))"` for a JSON deliverable.
- Actions (commit, push, save, send): the success line comes from tool output this turn (`git log -1 --oneline`, an HTTP 2xx, the returned id), not from having issued the command.
- Unrequested changes: `git status --short` and `git diff --stat` list only the files the request covers. A formatter, an IDE import sort, or a renamed symbol elsewhere is the usual tell (`git diff --stat` showing 40+ changed lines in a file you did not mean to edit). Revert them (`git checkout -- <file>`) or name them explicitly.

**Done when** every explicit ask maps to a line in the draft or to a one-line "skipped because", part counts match, every constraint was checked by a command, and `git status --short` lists only requested files.

## Examples

**Walked once.** Request: "Dedupe `contacts.csv` into `contacts-clean.csv` and tell me how many rows you removed." Draft: "Done: removed 1,284 duplicates, 9,716 rows remain." Depth: a number and a new file, so phases 1 and 2. Phase 1: the two counts came from a script whose output was capped at 40 lines, so they are inferred; `wc -l contacts.csv contacts-clean.csv` prints `11001` and `9717` (headers included): 11000 rows in, 9716 out, 1284 removed; the draft's numbers stand. Phase 2: asks are dedupe (file exists, `head -1` shows the header), the count (verified), the output name (`ls contacts-clean.csv`); `git status --short` lists only `contacts-clean.csv`. Send as is. Had the script's output been the only source, the line would read ``Unverified: 1,284 removed. Confirm with `wc -l contacts.csv contacts-clean.csv`.``

**Request:** "Add a retry to the upload call and update the README."
**Review finds:** retry added and tested; README untouched. → Gap in completeness. Update the README (or say explicitly it was skipped), then send.

**Request:** "How many rows does this CSV have?"
**Draft says:** "About 12,000." → Unverified claim. Run `wc -l` (minus header) and report the exact number.

**Request:** "Fix the failing date parser."
**Draft says:** "Fixed; tests pass." **Review finds:** no test run in this session. → Run `pytest tests/test_dates.py -q`; report the exit code and the pass/fail counts it printed, or say the tests were not run.

**Request:** "Rename `getUser` to `fetchUser`."
**Review finds:** the diff also reformats two unrelated files because the editor ran a formatter. → Unrequested change. Revert the formatting, keep the rename, then send.
