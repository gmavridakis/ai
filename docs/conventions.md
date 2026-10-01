# Writing a skill in this repo

Every skill here is a field manual the agent reaches for on its own: a short description that fires it, then a body of exact commands, tables, thresholds, and named failure modes with their tells. These rules say what a skill must look like before it is committed. They adapt the author's guide of [mattpocock/skills](https://github.com/mattpocock/skills) (`writing-for-agents`, MIT) to this repo's purpose: auto-loaded, procedural, stack-aware skills, maintained mostly by an unattended routine. `scripts/lint-skills.py` enforces the mechanical rules; the rest is judgement applied at review and refine time.

## 1. Two loads, one budget

- **Context load.** Every model-invoked description sits in context on every prompt in every project. A word in a description costs forever; a word in a body costs only when the skill fires.
- **Cognitive load.** A user-invoked skill (`disable-model-invocation: true` in the frontmatter) costs no context, but the user must remember that it exists and type `/name`. Spend it only where a human should decide to start something: an interview, a review, a hand-off.

Default to model-invoked. Make a skill user-invoked only when the agent should never start it on its own.

## 2. The description is a pointer

The description decides whether the skill fires; the body decides what happens next.

- At most 70 words for a model-invoked skill. At most 25 for a user-invoked one, written for the human reading the slash-command list, with no trigger list.
- Front-load the trigger: start with the verb or the thing ("Classify an error by layer", "Write, review, or fix Angular code").
- Verbatim tells are the strongest triggers (`NG0100`, `ERR_REQUIRE_ESM`, "Conflicting migrations"). List the ones that fire most; the full set lives in the body.
- One trigger per branch; collapse synonyms into one.
- End with a boundary clause, `Do not use …`, naming the sibling skill that owns the adjacent case, in at most 25 words. `gen-index.py` refuses a model-invoked skill without one.
- Nothing the body already says: no procedure, no rationale, no identity.

## 3. The body

Order: two sentences of framing (what fails and why the skill exists), numbered **phases** (`## 1.`, `## 2.`, …), unnumbered **reference** sections (tables, observation commands, anti-patterns), and `## Example` last. At most 150 lines in total; longer material goes to `references/<topic>.md` behind one pointer line.

- A phase is ordered work. Every phase ends with a line `**Done when** …` stating an observable state that is **checkable** (anyone can tell done from not done) and **exhaustive** ("every claim classified", not "claims reviewed"). "Understanding reached" is not a criterion; "one command that goes red, run once, output shown" is.
- Reference is consulted on demand and needs no criterion, but it carries an exhaustiveness bar where one applies ("match against every row").
- Hard artifacts: at least three things a competent agent could not guess, such as exact commands with flags, a decision table, numeric thresholds, or a named failure mode with its observable tell.
- At least one worked example with realistic input and output that walks the phases in order.
- Co-locate: a concept's definition, rules, and caveats live under one heading, not scattered.

## 4. Handoffs are operative

A handoff to another skill is a line the agent can execute, with its condition: `Call the Skill tool with "error-triage"`. One skill per call; a step that needs two skills says so and makes two calls. Only model-invoked skills can be called; a user-invoked precondition is phrased as "tell the user to run `/name`". A sibling named in the boundary clause is named again in the body with the condition that hands off to it.

## 5. Output templates

When the skill produces a document, report, or verdict, show the shape literally in a fenced block with `<placeholders>`. The agent copies a shape far more reliably than it follows a description of one. The template is the only place the shape is defined.

## 6. Leading words

Pick one word per skill that names its core move and use it as a token, never as a sentence. House words, shared across skills: *layer* (error-triage), *red* (a repro that fails on this bug), *tell* (the verbatim symptom), *pin* (versions before fixes), *row* (the matched table entry), *cap* (a bounded tool result), *snapshot* (state written before compaction), *claim* against *evidence*, *bar* and *pass rate*, *payload* (the literal that must survive compression). Coin a new word only with a definition on first use.

## 7. Pruning

- **Delta test.** A sentence a competent agent already follows by default is a no-op; delete the whole sentence. "Be careful", "think carefully", "make sure to", "be thorough" fail on sight.
- **Cache vs environment.** Never restate what `--help`, `package.json`, or a config file already says. Keep what the environment cannot tell the agent: the gotcha, the threshold, the reason, the symptom-to-cause link.
- **Single source of truth.** A fact lives in one skill; another skill points to it (`java-spring-stack` §2) instead of repeating it.
- **Relevance.** A line no branch reaches, or that has gone stale, is sediment; deleting it is a refinement. A table that will age carries its date, e.g. `(Sep 2026)`.
- **Positive form.** State the target behaviour. Keep a prohibition only as a hard guardrail, and pair it with the positive target so attention lands on what to do.

## 8. House style

- Imperative mood. Numbers over adjectives. The literal over a paraphrase.
- No em-dashes anywhere in the repo's prose. Rewrite with a colon, a comma, parentheses, or a new sentence; never a blind character substitution. En-dashes in ranges (`2–8/10`) are fine.
- Tables for branches (symptom → cause → fix, size → strategy); prose only for the framing.
- Verbatim tells in backticks exactly as printed; placeholders in `<angle brackets>`.

## 9. Conflict rules

1. One concern per skill: two skills firing on the same input is a conflict.
2. Every model-invoked description carries a boundary clause naming the owner of the adjacent case.
3. Adjacent skills name each other with the hand-off condition (§4), in both directions.
4. Merge threshold: more than roughly 70% shared trigger surface means one skill with phases, recorded under *Merges* in `README.md`.
5. Never two skills for one workflow stage.

## 10. Borrowed material

A skill adapted from another repo keeps a credits block in its frontmatter:

```yaml
metadata:
  credits:
    skill: grilling
    author: Matt Pocock
    url: https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md
    license: MIT
```

Adapt, never paste: the borrowed skill is rewritten to §2–§8 and to this repo's stacks, and its `CHANGELOG.md` entry says what changed from the original.

## 11. Done when a skill change is ready to commit

- [ ] `python3 scripts/lint-skills.py` exits 0; every warning is fixed or explained in the commit message.
- [ ] `python3 scripts/gen-index.py` has regenerated `skills/INDEX.md`.
- [ ] `README.md` has the skill's row, the `ROADMAP.md` item is ticked, and `CHANGELOG.md` has a line under today's date.
- [ ] The example was walked once against the phases: each **Done when** is reachable from the example's input.
