# Evaluation harness

Runs each skill against recorded cases with the real `claude` CLI on this machine, grades the result, and keeps a pass rate per skill so a refinement or a migration can be measured instead of eyeballed. Nothing here touches the repo's own files: every run happens in a temporary copy of the case's fixture.

## Requirements

- Python 3.10+ (`python --version`), no packages needed.
- Claude Code installed and logged in (`claude --version`; run `claude` once interactively if the first run asks for login).
- The skills linked into `~/.claude/skills` (`install.ps1` / `install.sh`), because the harness evaluates the skills **as installed**: a run uses exactly what a real session would see.
- Some fixtures run `python` (plain scripts, no packages). Nothing needs Node, Java, Django, npm or the network.

Runs use `--dangerously-skip-permissions` inside a throwaway directory under the system temp folder, with a per-run cap of 40 turns and 3 USD (`--max-turns`, `--budget-usd`).

## Run

```sh
python evals/run.py --all                        # every case, with the skill, 3 runs each (the baseline)
python evals/run.py --skill nodejs --runs 1      # one skill, quick check while editing it
python evals/run.py --skill routing              # trigger precision cases only
python evals/run.py --all --config both          # adds a without-skill run per case (claude -p --disable-slash-commands)
python evals/run.py --all --ref HEAD~5           # evaluate the SKILL.md files as they were at a git ref
python evals/run.py --skill error-triage --no-grade   # transcripts only; grade later
python evals/grade.py evals/results/<dir>        # grade (or regrade with --force) everything under a results dir
python evals/report.py evals/results/<new> --compare evals/results/<old>   # summary with deltas
```

On Windows use `python` from PowerShell or Git Bash; paths work either way.

Rough cost on a Sonnet-class model: a routing case 0.10 USD, a fixing case 0.30 to 1.50 USD, plus 0.10 per judged run. The full set (15 cases × 3 runs) is about 30 to 60 USD and 60 to 90 minutes; one skill is a few dollars and a few minutes. Run the full set before and after a migration, one skill while refining it.

## What a case is

`evals/cases/<folder>/evals.json` (the folder is a skill name, or `routing` for cross-skill trigger tests) holds a list of cases. Each case has:

- `prompt`: what the user types. Realistic, with the detail a real request carries.
- `fixture`: a directory copied into the temp workspace (logs, a small project, data files). `git_init: true` turns it into a repo first.
- `checks`: deterministic, graded by code. Types: `skill_fired`, `skill_not_fired`, `final_regex`, `transcript_regex`, `must_not_regex` (optionally `"where": "final"`), `tool_called` / `tool_not_called` (tool name plus a regex over the call's input), `order` (one regex must appear before another in the transcript), `file_exists`, `file_regex`, `file_not_regex` (on files the run created or changed), `files_changed_only`, `final_max_lines`, `read_uses_ranges`, `max_turns`.
- `expectations`: rubric lines graded by a judge model that reads the skill, the transcript and the outputs. Write one per phase, as that phase's `**Done when**` rephrased for the case, so the grade follows the skill's own completion criteria.
- `expected_output`: one sentence for the human reading the summary.

The deterministic checks are the ones to trust; the judge lines catch what regexes cannot (was the trace quoted before a hypothesis, was exactly one layer named). When the judge's `eval_feedback` says a line would also pass a wrong run, tighten it.

## What a run produces

`evals/results/<timestamp>/<skill>/<case>/<config>/run-<n>/`: `transcript.md` (readable), `final.md`, `metrics.json` (tool calls, skills fired, files changed), `timing.json` (seconds, tokens, cost), `grading.json` (every check and expectation with evidence), and `case.json` (the case as run, including the git ref). The raw `transcript.jsonl` and the `outputs/` copies stay local (gitignored); everything else is committed so the history of pass rates lives in the repo.

`summary.md` and `benchmark.json` at the top of the results directory aggregate everything: pass rate per case (mean ± stddev over runs), checks and judge counts, which skills fired, cost, time, and every expectation with its pass count. A line that passes in every run of every version is not discriminating; a line that fails in every run points at the skill or at the line.

## Reading a result

- `skills fired: none` on a skill's own case means the description did not trigger. That is a description problem (see `docs/conventions.md` §2), not a body problem, and the judge lines will all fail with it.
- Checks pass, judge fails: the model reached the right answer without following the phases. Decide whether the phase is worth enforcing, then sharpen its `**Done when**`.
- High variance (stddev ≥ 0.25 over 3 runs): the skill leaves a decision to chance. Find the step that differs between the passing and failing transcripts.
- `without_skill` close to `with_skill`: the skill fails the delta test on this case; either the case is too easy or the skill is.

## Workflow around a change

1. Before editing a skill: `python evals/run.py --skill <name>` (3 runs) and note the pass rate, or reuse the last committed results directory.
2. Edit the skill; lint; regenerate the index.
3. `python evals/run.py --skill <name>` again, then `python evals/report.py evals/results/<new> --compare evals/results/<old>`.
4. Commit the skill with the results directory and put the before/after pass rate in the `CHANGELOG.md` line.

A migrated skill (phase 2) gets its cases written first, is run against the original text from mattpocock/skills dropped into `skills/<name>/SKILL.md` as a baseline, and then against the adapted version.
