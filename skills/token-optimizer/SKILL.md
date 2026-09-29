---
name: token-optimizer
description: Choose the output form (diff, snippet, reference, or full file) and the tool-output report format that costs the fewest tokens without losing anything the user must act on. Use when the user asks for brevity or lower cost, when a reply is about to include more than ~20 lines of code, a file, or tool output that is already in context, or when a single reply would exceed ~150 lines. Do not use for deciding what to read, how to cap tool results, or when to compact — context-hygiene owns the input side; do not use when the user asks for a tutorial-style or exhaustive explanation, or when the reply must be self-contained for someone who will not see this conversation (a handover doc, an incident report, a bug report — bug-report-writing owns that).
---

# Token optimizer (output side)

This skill governs what you *emit*. What you *read* and when to compact is `context-hygiene` — hand off there when the window, not the reply, is the problem. Density never overrides correctness: shorten prose around literals, never the literals.

## 1. Pick the output form (decision table)

Measure first: `wc -l <file>` and the number of lines you will change.

| Situation | Emit | Never |
| --- | --- | --- |
| File does not exist yet, or user must copy‑paste it whole | full file | a diff against nothing |
| Change touches ≤ 30 % of lines **and** ≤ 40 lines | unified diff hunk(s), `// path:line` on the first line | the full file |
| Change touches > 30 % of lines or > 40 lines, file ≤ 150 lines | full file | scattered hunks the user must apply by hand |
| Change touches > 30 % of a file > 150 lines | apply it with an edit tool and report `path` + hunk count + one‑line summary | pasting either version into the reply |
| Content already in context (a file you read, a function the user pasted) | reference by `path:symbol` or `path:L10-L24` | re‑quoting it |
| Same edit in N files | one diff plus the list of paths it was applied to | N diffs |
| Multi‑hundred‑line implementation requested | interfaces/signatures first (≤ 40 lines), then ask which part to expand | the whole thing unprompted |

## 2. Report tool output, do not paste it

Rule: never paste more than 20 lines of tool output (test runs, logs, `ls`, `git diff`). Report in this shape:

```
<tool> → exit <code>; <N> of <M> <units> failed
first failure: <path:line> — <first line of the message>
full output: <path or "not saved">
```

Thresholds: a green run is one line (`npm test → exit 0; 212/212 passed, 4.1 s`). A red run is the shape above plus **at most 3** distinct failure lines; group identical messages (`×17 ECONNREFUSED 127.0.0.1:5432`). Save anything longer with `> /tmp/<name>.log 2>&1` and give the path.

## 3. What density must never cut

- Exact error messages, commands, paths, flags, version numbers — the literal is the payload.
- A file path (and line or enclosing function) on every snippet; a pathless diff costs the user a search.
- One sentence for any caveat that changes what the user should do (data loss, irreversible step, security). One is enough; zero is not.
- The stated assumption when you picked a form the user did not ask for ("applied directly, 3 hunks, no reply paste — say so if you want the diff").

## Examples

**Ask:** "Fix the null check in `parseUser` in src/auth.ts." (`wc -l` → 120; change = 1 line ⇒ row "≤ 30 % and ≤ 40 lines")

```ts
// src/auth.ts:42
- if (user.email.length > 0) {
+ if (user?.email?.length) {
```

One line of context: "`user` is undefined when the session cookie has expired."

**Ask:** "Run the tests." (`vitest` prints 340 lines)

```
vitest run → exit 1; 3 of 212 tests failed
first failure: test/orders.test.ts:88 — expected 200, received 500
also: test/orders.test.ts:104 (same cause: ECONNREFUSED 127.0.0.1:5432 ×3)
full output: /tmp/vitest.log
```

Not: the 340 lines, nor "Here are the results of running the tests:".
