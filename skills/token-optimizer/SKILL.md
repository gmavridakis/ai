---
name: token-optimizer
description: Produce dense, low-token responses and protect the context window. Use when the user asks for brevity or lower cost, when the conversation is long (roughly 50k+ tokens) or repeatedly re-reads large files, or when a reply would otherwise repeat code or content already in context. Do not use when the user asks for a tutorial-style or exhaustive explanation.
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
   - Do not re-read a file already in context unless it may have changed; read a line range or grep for the symbol instead of the whole file.
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

## Response Format Guidelines

- Use concise bullet points instead of prose paragraphs; a single-sentence answer needs no bullets at all.
- Keep code snippets scoped strictly to modified functions or blocks.
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
