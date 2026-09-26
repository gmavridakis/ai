---
name: response-self-review
description: Check a finished draft against the original request before sending it. Use when the draft is longer than ~5 lines, contains a code change, a created or edited file, a number or count, or a plan, or when the request had two or more parts or explicit constraints — to catch claims without evidence, unanswered parts, unrequested changes, and unstated assumptions. Do not use for one-line factual replies or acknowledgements; do not use it to trim length or density (token-optimizer owns that); and do not use it to validate a prompt written for another model — structured-prompting's test loop owns that.
---

# Response Self-Review

Review the draft as a skeptical reader who has only the original request, not your reasoning. Fix what you find, then send. Keep the review invisible: never narrate it in the final reply.

Pick the depth from the draft, not from how confident you feel:

| Draft contains | Run sections | Also |
| --- | --- | --- |
| ≤ 5 lines, no artifact, no number | none — send | — |
| a number, count, date, or version | 2 | recompute it |
| a code change or edited file | 2, 3 | `git diff --stat` vs. the files the request named |
| a new file, document, or plan | 1–4 | map every explicit ask to a line in the draft |

Never spend longer reviewing than drafting.

## 1. Re-read the request, not your memory of it

- Quote (to yourself) every explicit ask: verbs, deliverables, formats, counts, constraints ("under 150 lines", "as a table", "don't touch X").
- Note implied asks: audience, purpose, level of detail, language/locale, existing conventions in the codebase or document.
- Check whether the request changed mid-conversation; the latest instruction wins unless it contradicts a hard constraint.

## 2. Correctness

For each claim in the draft, classify it as verified (you ran, read, or searched it this session), inferred, or assumed. Every inferred or assumed claim is either verified now with the matching check, or labelled as unverified in the reply. There is no third option.

| Claim in draft | Evidence that counts | Not evidence |
| --- | --- | --- |
| "the code works" / "tests pass" | you ran it this turn and saw exit code 0 | it compiled; it looked right |
| a count, total, or date | output of `wc -l`, `grep -c`, a script, or `date -d` | arithmetic done in prose |
| a flag, path, signature, or version | `--help`, the file, or `pkg --version` shown in this session | memory |
| "I changed X" / "updated three tests" | `git diff --stat` and `git status --short` name exactly those files | your intent |
| a quoted line or error | the line as it appears in the tool output | a paraphrase |

Then read the draft once end-to-end for internal contradictions: a summary sentence that disagrees with its own table or list is the most common tell.

## 3. Completeness

- Map every explicit ask to the place in the draft that answers it. Any unmapped ask is a gap: answer it or state explicitly that you skipped it and why.
- Check the "and" cases: multi-part questions, lists of files, "for each" instructions.
- Confirm required output format (file type, structure, length, language) is exactly met, not approximated.
- If a task required an action (commit, send, save), confirm the action actually succeeded, not just that the command was issued.
- Check the reverse too: did you change, delete, or add anything the request did not cover (extra files touched, reformatting, renamed symbols)? Revert unrequested changes or call them out explicitly.

## 4. Assumptions

- List the choices you made where the request was ambiguous. For each: is it the most reasonable reading? Would a different reading change the answer materially?
- Surface material assumptions in one short line in the reply ("I assumed X; if Y, then ..."). Drop trivial ones.
- Do not present a guess as a fact; do not hedge a verified fact as a guess.

## 5. Decide

- All checks pass: send.
- A gap or error is found: fix it, then re-run only the checks the fix could have affected.
- Something cannot be verified in this turn: say what is unverified and how the user can confirm it, rather than silently sending.

## Examples

**Request:** "Add a retry to the upload call and update the README."
**Draft review finds:** retry added and tested; README untouched. -> Gap in completeness. Update README (or say explicitly it was skipped), then send.

**Request:** "How many rows does this CSV have?"
**Draft says:** "About 12,000." -> Unverified claim. Run `wc -l` (minus header) and report the exact number.

**Request:** "Fix the failing date parser."
**Draft says:** "Fixed; tests pass." **Review finds:** no test run in this session. -> Run `pytest tests/test_dates.py -q`; report the exit code and the pass/fail counts it printed, or say the tests were not run.

**Request:** "Rename `getUser` to `fetchUser`."
**Draft review finds:** the diff also reformats two unrelated files because the editor ran a formatter. -> Unrequested change. Revert the formatting, keep the rename, then send.

## Anti-patterns

- Reviewing your reasoning instead of the draft the user will read.
- Treating "I intended to do X" as evidence that X was done.
- Adding a "Summary of checks performed" section to the reply.
- Rewriting the whole draft when a targeted fix would do.
