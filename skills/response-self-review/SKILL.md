---
name: response-self-review
description: Verify a finished draft against evidence before sending it. Use when the draft asserts a result you did not observe in tool output this turn ("tests pass", "fixed", a count, a version, "updated the README"), contains a code change or an edited/created file, or answers a request with two or more parts or an explicit format/length constraint — to catch claims without evidence, unanswered parts, and unrequested changes. Do not use for one-line factual replies or acknowledgements; do not use it to trim length or density (token-optimizer owns that); and do not use it to validate a prompt written for another model — structured-prompting's test loop owns that.
---

# Response Self-Review

Review the draft as a skeptical reader who has only the original request, not your reasoning. Fix what you find, then send. Keep the review invisible: never narrate it in the final reply.

Pick the depth from the draft, not from how confident you feel:

| Draft contains | Run sections | Also |
| --- | --- | --- |
| ≤ 5 lines, no artifact, no number | none — send | — |
| a number, count, date, or version | 1 | recompute it with a command, not in prose |
| a code change or edited file | 1, 2 | `git diff --stat` must list only files the request named |
| a new file, document, or plan | 1, 2 | map every explicit ask to a line in the draft |

Budget: at most 3 tool calls per review and no re-drafting — fix in place. If a check needs more than that, send with the item marked unverified and how the user can confirm it.

## 1. Correctness

For each claim in the draft, classify it as verified (you ran, read, or searched it this session), inferred, or assumed. Every inferred or assumed claim is either verified now with the matching check, or labelled as unverified in the reply. There is no third option.

| Claim in draft | Evidence that counts | Not evidence |
| --- | --- | --- |
| "the code works" / "tests pass" | you ran it this turn and saw exit code 0 | it compiled; it looked right |
| a count, total, or date | output of `wc -l`, `grep -c`, a script, or `date -d` | arithmetic done in prose |
| a flag, path, signature, or version | `--help`, the file, or `pkg --version` shown in this session | memory |
| "I changed X" / "updated three tests" | `git diff --stat` and `git status --short` name exactly those files | your intent |
| a quoted line or error | the line as it appears in the tool output | a paraphrase |

Then read the draft once end-to-end for internal contradictions: a summary sentence that disagrees with its own table or list is the most common tell.

## 2. Completeness

- Map every explicit ask (verbs, deliverables, formats, counts, constraints such as "under 150 lines", "as a table", "don't touch X") to the line in the draft that answers it. An unmapped ask is a gap: answer it or state in one line that it was skipped and why.
- Multi-part requests: count the parts ("and", numbered items, "for each") and count the answers; the numbers must match.
- Length/format constraints: check with a command, not by eye — `wc -l file`, `head -c 300 file` for the required opening, `python -c "import json;json.load(open('x.json'))"` for a JSON deliverable.
- Actions (commit, push, save, send): the success line must come from tool output this turn (`git log -1 --oneline`, an HTTP 2xx, the returned id), not from having issued the command.
- Unrequested changes: `git status --short` and `git diff --stat` must list only the files the request covers; a formatter, an IDE import sort, or a renamed symbol elsewhere is the usual tell (`git diff --stat` showing 40+ changed lines in a file you did not mean to edit). Revert them (`git checkout -- <file>`) or name them explicitly.

## Examples

**Request:** "Add a retry to the upload call and update the README."
**Draft review finds:** retry added and tested; README untouched. -> Gap in completeness. Update README (or say explicitly it was skipped), then send.

**Request:** "How many rows does this CSV have?"
**Draft says:** "About 12,000." -> Unverified claim. Run `wc -l` (minus header) and report the exact number.

**Request:** "Fix the failing date parser."
**Draft says:** "Fixed; tests pass." **Review finds:** no test run in this session. -> Run `pytest tests/test_dates.py -q`; report the exit code and the pass/fail counts it printed, or say the tests were not run.

**Request:** "Rename `getUser` to `fetchUser`."
**Draft review finds:** the diff also reformats two unrelated files because the editor ran a formatter. -> Unrequested change. Revert the formatting, keep the rename, then send.
