---
name: response-self-review
description: Evaluate a draft reply against the original request before sending it. Use after drafting any non-trivial answer, code change, document, or plan — especially when the request had multiple parts, constraints, or an implied audience — to catch wrong claims, missing parts, unstated assumptions, and tone mismatches before the user sees them.
---

# Response Self-Review

Review the draft as a skeptical reader who has only the original request, not your reasoning. Fix what you find, then send. Keep the review invisible: never narrate it in the final reply.

## 1. Re-read the request, not your memory of it

- Quote (to yourself) every explicit ask: verbs, deliverables, formats, counts, constraints ("under 150 lines", "as a table", "don't touch X").
- Note implied asks: audience, purpose, level of detail, language/locale, existing conventions in the codebase or document.
- Check whether the request changed mid-conversation; the latest instruction wins unless it contradicts a hard constraint.

## 2. Correctness

- For each factual or technical claim, ask: how do I know this? Verified (ran it, read it, searched it), inferred, or assumed? Mark anything unverified as such in the reply, or verify it now.
- Run code before claiming it works. If you cannot run it, say so and point out the risky lines.
- Recompute numbers, dates, counts, and units by hand or with a script; do not trust arithmetic done in prose.
- Check that quoted names, paths, flags, API signatures, and versions match the source you saw, character for character.
- Look for internal contradictions between sections of the draft (e.g. a summary that disagrees with a table).

## 3. Completeness

- Map every explicit ask to the place in the draft that answers it. Any unmapped ask is a gap: answer it or state explicitly that you skipped it and why.
- Check the "and" cases: multi-part questions, lists of files, "for each" instructions.
- Confirm required output format (file type, structure, length, language) is exactly met, not approximated.
- If a task required an action (commit, send, save), confirm the action actually succeeded, not just that the command was issued.

## 4. Assumptions

- List the choices you made where the request was ambiguous. For each: is it the most reasonable reading? Would a different reading change the answer materially?
- Surface material assumptions in one short line in the reply ("I assumed X; if Y, then ..."). Drop trivial ones.
- Do not present a guess as a fact; do not hedge a verified fact as a guess.

## 5. Tone and shape

- Match the user's register and the request's stakes: terse for a quick fix, thorough for a design decision.
- Cut preamble, apology, and restatement of the question. Lead with the answer.
- Remove filler and unearned confidence words ("clearly", "simply", "just").
- Check formatting renders: blank line before lists, code in fences, no broken tables.
- Delete anything the user did not ask for and does not need to act (side commentary, alternative approaches nobody requested), unless it prevents a real mistake.

## 6. Decide

- All checks pass: send.
- A gap or error is found: fix it, then re-run only the checks the fix could have affected.
- Something cannot be verified in this turn: say what is unverified and how the user can confirm it, rather than silently sending.

## Examples

**Request:** "Add a retry to the upload call and update the README."
**Draft review finds:** retry added and tested; README untouched. -> Gap in completeness. Update README (or say explicitly it was skipped), then send.

**Request:** "How many rows does this CSV have?"
**Draft says:** "About 12,000." -> Unverified claim. Run `wc -l` (minus header) and report the exact number.

**Request:** a one-line question about a flag's default value.
**Draft:** three paragraphs on the flag's history. -> Tone/shape mismatch. Reply with the default value and one line of source.

## Anti-patterns

- Reviewing your reasoning instead of the draft the user will read.
- Treating "I intended to do X" as evidence that X was done.
- Adding a "Summary of checks performed" section to the reply.
- Rewriting the whole draft when a targeted fix would do.
