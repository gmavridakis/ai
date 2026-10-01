---
name: token-optimizer
description: Choose the cheapest output form and how to report tool output, keeping everything the user must act on. Use when the user wants brevity or lower cost, when a reply would include more than 20 lines of code or tool output already in context, or would exceed 150 lines. Do not use for what to read or when to compact (context-hygiene), tutorials, or a self-contained handover (bug-report-writing).
---

# Token optimizer (output side)

This skill governs what you *emit*. Density never overrides correctness: shorten the prose around literals, never the literals; the literal is the *payload*.

The window, not the reply, is the problem: Call the Skill tool with "context-hygiene". The reply must stand alone for someone outside this conversation (an upstream issue, a vendor ticket): Call the Skill tool with "bug-report-writing".

## 1. Pick the output form

Measure first: `wc -l <file>` and the number of lines you will change. Then match every row:

| Situation | Emit | Never |
| --- | --- | --- |
| File does not exist yet, or user must copy‑paste it whole | full file | a diff against nothing |
| Change touches ≤ 30 % of lines **and** ≤ 40 lines | unified diff hunk(s), `// path:line` on the first line | the full file |
| Change touches > 30 % of lines or > 40 lines, file ≤ 150 lines | full file | scattered hunks the user must apply by hand |
| Change touches > 30 % of a file > 150 lines | apply it with an edit tool and report `path` + hunk count + one‑line summary | pasting either version into the reply |
| Content already in context (a file you read, a function the user pasted) | reference by `path:symbol` or `path:L10-L24` | re‑quoting it |
| Same edit in N files | one diff plus the list of paths it was applied to | N diffs |
| Multi‑hundred‑line implementation requested | interfaces/signatures first (≤ 40 lines), then ask which part to expand | the whole thing unprompted |

**Done when** `wc -l` and the changed-line count are known and exactly one row's *Emit* column is what the reply contains.

## 2. Report tool output in the fixed shape

Rule: never paste more than 20 lines of tool output (test runs, logs, `ls`, `git diff`). Report in this shape:

```
<tool> → exit <code>; <N> of <M> <units> failed
first failure: <path:line>: <first line of the message>
full output: <path or "not saved">
```

Thresholds: a green run is one line (`npm test → exit 0; 212/212 passed, 4.1 s`). A red run is the shape above plus **at most 3** distinct failure lines; group identical messages (`×17 ECONNREFUSED 127.0.0.1:5432`). Save anything longer with `> /tmp/<name>.log 2>&1` and give the path.

**Done when** every tool result mentioned in the reply is in the shape above, at most 20 lines, and anything longer has a saved path.

## What density must never cut

- Exact error messages, commands, paths, flags, version numbers: the literal is the payload.
- A file path (and line or enclosing function) on every snippet; a pathless diff costs the user a search.
- One sentence for any caveat that changes what the user should do (data loss, irreversible step, security). One is enough; zero is not.
- The stated assumption when you picked a form the user did not ask for ("applied directly, 3 hunks, no reply paste; say so if you want the diff").

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
first failure: test/orders.test.ts:88: expected 200, received 500
also: test/orders.test.ts:104 (same cause: ECONNREFUSED 127.0.0.1:5432 ×3)
full output: /tmp/vitest.log
```

Not the 340 lines, and not "Here are the results of running the tests:".
