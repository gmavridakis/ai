---
name: documentation-writing
description: Write a document people will act on: a README, quickstart, ADR, runbook, onboarding or CONTRIBUTING page, config reference. Use when asked to "document this", "write a README", "add a runbook for", "record the decision", "update the docs", or when "how do I run this" has no answer in the repo. Do not use for a bug report (bug-report-writing), a prompt or CLAUDE.md block (structured-prompting), or to shorten a reply (token-optimizer).
---

# Documentation Writing

Docs go unread for two reasons: the page answers no question a reader arrives with, or its commands were typed from memory and fail on the first run. This skill names the reader first, picks the one document type that answers them, fills it only with commands run in this session, and proves it in a clean environment. The leading word is **reader**: one named person, the question they bring, the action they must be able to take when they leave.

Entry: the subject exists and runs today. The text is a bug for people outside this conversation: Call the Skill tool with "bug-report-writing". It is a system prompt, subagent brief or `CLAUDE.md` block that a model will read: Call the Skill tool with "structured-prompting". The user wants a shorter chat reply, not a document: Call the Skill tool with "token-optimizer". The doc describes a code change the user still has to make: write the code first, then return here. The text asked for is an estimate, a plan with a range, or "how long will it take": Call the Skill tool with "estimation-and-scoping"; return here only for the ADR that records the chosen option. The document is a postmortem of an incident: Call the Skill tool with "incident-response" (its phase 5 owns the template); return here for the runbook its action items ask for.

## 1. Name the reader and pick one type

Write one line before anything else: `Reader: <role>, arrives with "<question>", leaves able to <action>`. Then find what already answers it so the repo keeps one source: `git ls-files '*.md' '*.rst' '*.adoc' | xargs grep -il '<topic>'`. A hit is the file to edit; a doc written beside it is a duplicate from day one. Pick the row by the question, never by the name the user used ("write a README" that answers "why Kafka" is an ADR).

| Reader's question | Type | Lives at | First-screen rule |
| --- | --- | --- | --- |
| "How do I run this in 10 minutes?" | README quickstart | `README.md` | the first 30 lines carry one-line purpose, install, run, and the first expected output |
| "How do I do task X here?" | how-to | `docs/<task>.md` | numbered steps, each a command plus its expected output line |
| "What does option Y mean?" | reference | `docs/config.md` or a table in README | one row per key: name, type, default, effect, where read |
| "Why did we choose Z?" | ADR | `docs/adr/NNNN-<slug>.md` | status and date in the first 5 lines; options compared, not just the winner |
| "The alert fired, what now?" | runbook | `docs/runbooks/<alert-name>.md` | symptom, check command, fix command, rollback, escalation; nothing to read before step 1 |
| "How do I start contributing?" | onboarding | `CONTRIBUTING.md` | clone-to-first-green-test in one block |

**Done when** the reader line is written, the type row is named, and the `git ls-files` grep result is recorded as "edit `<file>`" or "no hit".

## 2. Lay out the template literally

Copy the shape for the row and keep every heading; delete a heading only with the reason in the commit message. Headings are what a reader scans, so a renamed heading costs more than an empty one.

 ```markdown
 # <project>: <what it does in one line, no adjectives>
 ## Quickstart
 <install command>            # <first output line>
 <run command>                # <first output line>
 ## Configuration
 | Key | Type | Default | Effect | Read in |
 ## Develop
 <test command>               # <count line>
 ## Where things are
 <path>: <one line>
 ```

 ```markdown
 # <NNNN>. <decision as a verb phrase>
 Status: <proposed | accepted | superseded by NNNN> · Date: <YYYY-MM-DD> · Deciders: <names>
 ## Context and problem statement
 ## Decision drivers
 ## Considered options
 ## Decision outcome
 Chosen: <option>, because <driver>. Confirmation: <command or review that proves it is applied>.
 ### Consequences
 ## Pros and cons of the options
 ```

 ```markdown
 # Runbook: <alert name as it appears in the pager>
 Severity: <S1..S4> · Owner: <team> · Last tested: <YYYY-MM-DD>
 ## Symptom
 <verbatim alert text or log line>
 ## Check
 <command>                    # healthy: <output>   firing: <output>
 ## Fix
 1. <command>                 # expect: <output>
 ## Rollback
 ## Escalate
 <who> when <condition after N minutes>
 ```

**Done when** the file holds every heading of its template, in order, with placeholders still visible where phase 3 has not filled them.

## 3. Fill with what ran, not what is remembered

Every fenced command in the doc is pasted from a run in this session and followed by its first output line as a comment. A config table is generated, not recalled:

| Stack | Keys the code reads |
| --- | --- |
| Node | `git grep -hoE 'process\.env\.[A-Z0-9_]+' -- src \| sort -u` |
| Python | `git grep -hoE "(os\.environ(\.get)?\[?\(?['\"][A-Z0-9_]+|env\(['\"][A-Z0-9_]+)" \| grep -oE '[A-Z0-9_]{3,}' \| sort -u` |
| Spring | `git grep -hoE '@Value\("\$\{[a-z0-9.-]+' -- src \| sed 's/.*{//' \| sort -u` plus every key in `application*.yml` |

Each key gets its row; a key with no default in the code gets `required` in the Default column, which is the row that saves the reader an hour. Versions and dates are literals (`Node 22.14`, `Boot 3.4.2`, `(Oct 2026)`), never "latest". A line that restates `--help` or the code comment is deleted; keep the gotcha, the threshold and the reason.

**Done when** every fenced command has an output comment from this session, every config row traces to one grep hit, and `grep -nE 'TODO|TBD|latest|simply|just run' <file>` prints nothing.

## 4. Prove it as the reader

Run the quickstart or runbook in a clean environment, never in the working tree where it was written: `docker run --rm -v "$PWD":/w -w /w <image> sh -c '<install> && <run>'` with `node:22-alpine`, `python:3.12-slim`, `eclipse-temurin:21` or `ghcr.io/cirruslabs/flutter:stable`; without Docker, `git clone <repo> /tmp/fresh && cd /tmp/fresh`. Time it with `time`. Then the three checks:

| Check | Command | Passing tell |
| --- | --- | --- |
| Links | `lychee --no-progress --exclude-path node_modules '**/*.md'` | last line `0 Errors`; a `✗ [404]` or `✗ [ERR]` line names the dead link |
| Markdown | `npx markdownlint-cli2 '**/*.md' '#node_modules'` (`--fix` for the mechanical ones) | `Summary: 0 error(s)`; `MD041` means the file does not start with its title |
| Style | `vale sync && vale --minAlertLevel=error <file>` (needs a `.vale.ini`; skip when absent) | `✔ 0 errors` |

First screen: `head -30 README.md` must show install, run and the first expected output; a runbook's `## Check` command must sit above line 15.

**Done when** the clean-environment run exits 0 in under 10 minutes with the output the doc promises, lychee prints `0 Errors`, markdownlint prints `0 error(s)`, and the first-screen rule of the type row holds.

## 5. Place, link, and retire the duplicate

Put the file at the path in the type table; a new ADR takes the next number (`ls docs/adr | tail -1`). Link it from one parent (README "Where things are", `docs/adr/README.md` index, the alert's annotation in the monitoring config). The phase 1 hit, if the new file supersedes it, is deleted in the same commit or reduced to one pointer line. Before the reply claims "docs updated": Call the Skill tool with "response-self-review".

**Done when** `git grep -il '<topic>' -- '*.md'` lists the new file and at most one pointer, the parent links to it, and the commit holds the doc, its link and the deletion together.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| `## Introduction` restating the project name | the one-line purpose in the title; delete the section |
| A command with no output line after it | run it; paste the first line (the reader uses it to know they are on track) |
| A screenshot of a terminal | the text, in a fenced block |
| "Install the dependencies as usual" | the exact command for this repo's manager |
| A config table copied from a vendor's docs | the grep row in phase 3; only keys this code reads |
| README over 300 lines | quickstart stays; each other section becomes `docs/<topic>.md` with one pointer line |
| ADR with the winner only | the options table; an ADR with one option is a changelog line |

## Example

**Ask:** "New people keep asking how to run the billing service locally; write a README."

1. Reader: `backend developer on day 1, arrives with "how do I run billing locally", leaves able to see one invoice served on localhost`. Type row: README quickstart. `git ls-files '*.md' | xargs grep -il billing` hits `docs/setup-old.md` (2024, references Boot 2.7): edit target is `README.md`, `docs/setup-old.md` to retire.
2. README template laid out with the five headings; placeholders left in Configuration.
3. `./mvnw -q -B spring-boot:run` run in session: first output line `Started BillingApplication in 6.2 seconds`; `curl -s localhost:8080/invoices/1 | head -c 80` pasted with its JSON. `git grep -hoE '@Value\("\$\{[a-z0-9.-]+' -- src` prints 4 keys; `billing.stripe.key` has no default: row says `required`. The grep for `TODO|TBD|latest|simply|just run` prints nothing.
4. `docker run --rm -v "$PWD":/w -w /w eclipse-temurin:21 sh -c './mvnw -q -B spring-boot:run'` fails: `Missing required property billing.stripe.key`. Quickstart gains `export BILLING_STRIPE_KEY=sk_test_x` above the run line; rerun exits 0 in 4m10s. `lychee --no-progress '**/*.md'` prints `✗ [404] https://wiki.internal/billing` from the old doc, which goes away with it; rerun `0 Errors`. markdownlint `0 error(s)`. `head -30 README.md` shows install, run and the `Started BillingApplication` line.
5. `docs/setup-old.md` deleted in the same commit; `git grep -il billing -- '*.md'` lists `README.md` only. response-self-review confirms the "docs updated" claim against the diff.
