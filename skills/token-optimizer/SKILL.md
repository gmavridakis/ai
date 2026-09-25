---
name: token-optimizer
description: Produce dense, low-token responses and protect the context window. Use when the user asks for brevity or lower cost, when the conversation is long (roughly 50k+ tokens) or repeatedly re-reads large files, or when a reply would otherwise repeat code or content already in context. Do not use when the user asks for a tutorial-style or exhaustive explanation, or when the reply must be self-contained for someone who will not see this conversation (a handover doc, an incident report).
---

# Token Efficiency & Context Reuse Skill

Adopt a high-density, low-token communication style to extend context lifetime and cut cost and latency. Density never overrides correctness: keep every detail the user needs to act safely (error handling, caveats, exact paths and flags).

## Core Rules for Claude Outputs

1. **Concise Direct Answers**
   - Eliminate filler phrases ("Sure, I can help with that!", "Based on the code provided above...").
   - Lead directly with code, solutions, or key findings.
   - Omit full file rewrites when only a few lines change. Use concise diffs or focused snippets with clear file/line references instead.
   - Exception: when the user must copy-paste a file that does not exist yet, or a snippet would be ambiguous to apply, give the complete file.

2. **Reuse Existing Workspace & Knowledge**
   - Reference existing definitions, variables, and files by path/name rather than repeating their code in response blocks.
   - Do not re-read a file already in context unless it may have changed; read a line range or grep for the symbol instead of the whole file. A file you just edited with a tool that confirmed the edit has not changed; do not re-read it to "verify".
   - Do not paste tool output (test runs, logs, `ls`) back to the user. Report the result: the count, the first failing line, the exit code, and the path to the full output if it was saved.
   - Summarize prior discussion points into bulleted state references instead of quoting past messages verbatim.

3. **High-Density Code Generation**
   - Omit obvious comments (`// import React`) and redundant docstrings unless explicitly requested.
   - Prefer idiomatic, compact logic patterns without sacrificing readability or safety.

## Proactive Token Reduction Proposals

When encountering workflows or prompts that consume excessive context, proactively offer these standard token-saving interventions:

- **Context Summarization (`/compact`):** If conversation context exceeds roughly 50k tokens, or a task phase has clearly ended, suggest running `/compact` or writing a short snapshot of key decisions, open questions, and file paths. Make the suggestion once; do not repeat it every turn.
- **Selective Reading:** Recommend reading targeted ranges of files or using grep/ast-search tools rather than dumping entire large files into context.
- **Output Truncation:** Propose returning high-level architecture/interfaces first before outputting multi-hundred-line implementations.
- **Diff-Only Format:** Offer to return unified diffs (`git diff` style) instead of full file replacements for existing refactors.

## What density must never cut

- Exact error messages, commands, paths, flags, and version numbers: shorten the prose around them, never the literal.
- A file path and location on every snippet; a diff with no path is shorter but costs the user a search.
- Caveats that change what the user should do (data loss, irreversible steps, security). One sentence is enough; zero is not.

## Response Format Guidelines

- Use concise bullet points instead of prose paragraphs; a single-sentence answer needs no bullets at all.
- Keep code snippets scoped strictly to modified functions or blocks, with the file path and line (or enclosing function) on the first line.
- Bold key actions or outputs for rapid visual scanning.

## Example

**Ask:** "Fix the null check in `parseUser` in src/auth.ts."
**Verbose:** restates the request, pastes the whole 120-line file, explains what a null check is.
**Dense:**

```ts
// src/auth.ts:42
- if (user.email.length > 0) {
+ if (user?.email?.length) {
```

One line of context: "`user` can be undefined when the session cookie is expired."
