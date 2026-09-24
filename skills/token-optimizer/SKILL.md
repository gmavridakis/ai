---
name: token-optimizer
description: Optimizes response density, minimizes output verbosity, reuses context, and proactively suggests token-reduction techniques for large prompts or context windows.
---

# Token Efficiency & Context Reuse Skill

When this skill is active or invoked, adopt a high-density, low-token communication strategy designed to maximize context lifetime and minimize billing/latency costs.

## Core Rules for Claude Outputs

1. **Concise Direct Answers**
   - Eliminate filler phrases ("Sure, I can help with that!", "Based on the code provided above...").
   - Lead directly with code, solutions, or key findings.
   - Omit full file rewrites when only a few lines change. Use concise diffs or focused snippets with clear file/line references instead.

2. **Reuse Existing Workspace & Knowledge**
   - Reference existing definitions, variables, and files by path/name rather than repeating their code in response blocks.
   - Summarize prior discussion points into bulleted state references instead of quoting past messages verbatim.

3. **High-Density Code Generation**
   - Omit obvious comments (`// import React`) and redundant docstrings unless explicitly requested.
   - Prefer idiomatic, compact logic patterns without sacrificing readability or safety.

## Proactive Token Reduction Proposals

When encountering workflows or prompts that consume excessive context, proactively offer these standard token-saving interventions:

- **Context Summarization (`/compact`):** If conversation context exceeds 50k tokens, suggest running `/compact` or taking a snapshot of key decisions.
- **Selective Reading:** Recommend reading targeted ranges of files or using grep/ast-search tools rather than dumping entire large files into context.
- **Output Truncation:** Propose returning high-level architecture/interfaces first before outputting multi-hundred-line implementations.
- **Diff-Only Format:** Offer to return unified diffs (`git diff` style) instead of full file replacements for existing refactors.

## Response Format Guidelines

- Use concise bullet points instead of prose paragraphs.
- Keep code snippets scoped strictly to modified functions or blocks.
- Bold key actions or outputs for rapid visual scanning.