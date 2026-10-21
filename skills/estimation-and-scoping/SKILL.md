---
name: estimation-and-scoping
description: Estimate a piece of work as a range with its scope and unknowns named. Use when asked "how long will this take", "estimate", "scope this", "break this work down", "t-shirt size", "story points", "can we do it this sprint", or "is this feasible". Do not use to split a file (safe-refactoring), to record the decision (documentation-writing), while users are failing now (incident-response), or to do the work itself.
---

# Estimation and Scoping

A single number given from the description of a task is a guess dressed as a commitment: the touch points were never counted, the review and deploy time were never included, and the one unknown that doubles the work was never written down. The leading word is **range**: a low and a high the evidence supports, never one number.

Entry: the ask is a change to a system you can inspect (the repo, its history, its tracker). "How long to fix this" with the cause unknown: Call the Skill tool with "error-triage" first and estimate from its layer. "Prod is down, how long to fix" with users failing now: Call the Skill tool with "incident-response"; the time to mitigate is its update line, and the fix is estimated here only once its status is `monitoring`. The user wants the pieces of one file or function, not of the work: Call the Skill tool with "safe-refactoring". The estimate is accepted and the choice behind it needs a record: Call the Skill tool with "documentation-writing" for the ADR.

## 1. Pin the ask and its maturity

Write three lines before any number: `Ask: <one sentence>`, `Done means: <observable the user can check>`, `Out: <at least one thing a reader could assume is included and is not>`. Then pick the maturity row below from what exists today, not from what the user hopes to have by Friday. The row fixes the minimum width of the final range; a narrower range at that row is a promise the evidence cannot keep.

| What exists today | Row | Low × likely | High × likely |
| --- | --- | --- | --- |
| One sentence, no acceptance criteria | concept | 0.25 | 4 |
| Acceptance criteria written and agreed | defined | 0.5 | 2 |
| Touch points counted (phase 2 done) | measured | 0.67 | 1.5 |
| Slices with a Done-when each (phase 4 done) | sliced | 0.8 | 1.25 |
| Every unknown resolved by a spike | resolved | 0.9 | 1.1 |

(McConnell's cone of uncertainty, adapted to task-sized work.)

**Done when** the three lines are written, `Out:` names at least one exclusion, and the row is named with its two multipliers.

## 2. Measure the scope

Count what the change touches; a number from a command replaces an adjective every time. Run the rows that apply and keep the output lines:

| Question | Command | Reading |
| --- | --- | --- |
| How big is the area | `git ls-files '<dir>' \| xargs wc -l \| tail -1` | over 5,000 lines: budget a reading slice before any coding slice |
| How many call sites change | `git grep -n '<symbol>' -- ':!*test*' \| wc -l` | over 20: a parallel change (safe-refactoring owns the step) |
| How many files change | `git grep -l '<symbol>' \| wc -l` (write it down as `files=<n>`; it filters phase 3) | over 10: add a slice per package or layer, not one slice for the rename |
| What tests cover it | `git ls-files '*test*' '*spec*' \| xargs grep -ln '<symbol>' \| wc -l` | `0`: add a characterization-test slice first, it is scope |
| Who knows it | `git log --since=1.year --format=%an -- <dir> \| sort \| uniq -c \| sort -rn \| head -3` | one name, not you: add a review-wait row from phase 3 |
| How often it changes | `git log --since=90.days --oneline -- <dir> \| wc -l` | over 30: expect merge conflicts; slices stay short-lived |
| Schema or data involved | `git ls-files '*migration*' '*migrations/*' \| grep -c '<table>'` | any hit: migration plus backfill plus rollback is its own slice |

Hidden scope is scope: tests, migration and backfill, review and CI wait, docs, feature flag or rollout, monitoring. Each one the ask needs gets a slice in phase 4; "the last 10%" is where single-number estimates die.

**Done when** every applicable row has its number pasted, `files=<n>` is written, and each hidden-scope item is marked `slice` or `out`.

## 3. Build the reference class

Your gut is calibrated on the happy path; the repo's history is calibrated on reality. Pull the merged changes most like this one and read how long they took from open to merge:

```sh
gh pr list --state merged --limit 200 --search '<keyword>' \
  --json number,title,createdAt,mergedAt,additions,deletions,changedFiles \
  | jq -r '.[] | [.number, (((.mergedAt|fromdate)-(.createdAt|fromdate))/8640|round/10), (.additions+.deletions), .changedFiles, .title] | @tsv' \
  | awk -F'\t' -v f=<files> '$4 >= f/3 && $4 <= f*3' | sort -t$'\t' -k2 -n | tee ref.tsv \
  | awk -F'\t' '{a[NR]=$2} END{print "n="NR, "median="a[int((NR+1)/2)], "p80="a[int(NR*0.8+0.5)]}'
```

Columns: PR, lead time in days, changed lines, files, title. Without `gh`: `git log --merges --first-parent --date=short --format='%ad %s' -- <dir> | head -20` gives dates; lead time then comes from the first commit of each branch (`git log --format=%ad --date=short <merge>^2 | tail -1`). The `-v f=<files>` filter keeps PRs whose file count is within 3× of phase 2's `files=`; a PR that touched 40 files is not a reference for one that touches 4. Lead time includes review and CI wait, which is why it is the reference and coding time is not. Fewer than 3 rows: write `Reference: none` and move the maturity row one step up the table (wider).

**Done when** `ref.tsv` holds at least 3 rows that passed the file-count filter, with `n=`, `median=`, `p80=` printed, or `Reference: none` is written with the widened row.

## 4. Slice, then classify the unknowns

Cut the work into vertical slices (each one usable or demonstrable on its own) of at most 2 days or 200 changed lines, whichever comes first; a slice that cannot be cut that small is itself an unknown. Give each slice a Done-when the user could check. Then list every question that changes the estimate and resolve it by its type:

| Unknown | Resolve by | Timebox |
| --- | --- | --- |
| "Does the library or API support X" | spike: a 30-line script against the real dependency, kept under `spikes/` | 2 hours |
| "How does this code path behave" | read it with a failing test as the probe | half a day |
| "Will the data fit the new shape" | `SELECT count(*)` of the rows that break the rule, on a production copy | 2 hours |
| "What does the stakeholder mean by Y" | one question with a recommended answer, sent today; estimate both branches until answered | 0 (waiting is not work) |
| "Is it fast enough" | a baseline measurement: Call the Skill tool with "performance-profiling" | half a day |
| "Who approves the schema change" | ask; a review-wait row from phase 3 covers the delay | 0 |

Total spike time stays under 10% of the likely total and under 1 day; a larger spike is the first slice of the work, estimated as such.

**Done when** every slice has O/M/P in one unit, is at most 2 days or 200 lines, carries a Done-when, and every unknown has a row with a timebox.

## 5. Compute the range and report

Per slice: optimistic O, most likely M, pessimistic P in one unit (hours or days, never mixed). Likely total E = Σ(O + 4M + P)/6; low = Σ O, high = Σ P. Then widen to the maturity row: if `low > E × low-multiplier`, lower it; if `high < E × high-multiplier`, raise it. Reference check: if E is under half the reference median, the median wins as E and the reply says so; your slices missed something the history did not. A gut number the user offered ("should be quick, right?") is written under Assumptions, never used as an input.

```
Estimate: <ask in one line>
Range: <low>–<high> <unit>, likely <E> (<maturity row>, reference median <d> days, p80 <d> days | Reference: none)
Scope: <n> files, <n> call sites, <n> tests touched. Out: <exclusion>, <exclusion>
Slices (each <= 2 days):
  1. <slice>: <O>/<M>/<P> <unit>, done when <observable>
Unknowns: <question>: <resolve by>, <timebox> | none
Assumptions: <one per line, including any number the user offered>
```

Before sending: Call the Skill tool with "response-self-review" so each number traces to a command output or a slice line.

**Done when** the block is in the reply with low, E and high satisfying the row's multipliers, the reference check recorded, and response-self-review has run.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| One number ("about 3 days") | the range block; the row multipliers are the minimum width |
| Hours per slice from the description alone | phase 2 numbers pasted beside each slice |
| "Plus some time for tests and review" | a slice for tests and a review-wait row from the reference lead time |
| A spike with no end | the timebox column; at the limit, record the branch assumed and continue |
| Shrinking the range to fit the sprint | the range stays; the `Out:` line grows until the high fits |
| Points or t-shirt sizes with no reference | the same block; map E to the team's scale last, in the Assumptions line |
| A slice runs past 2× its P and the range is left as sent | re-run phase 5 with the actual for every finished slice in place of O/M/P; the row moves to `measured` and the new block replaces the old one in the thread |

## Example

**Ask:** "Product wants CSV export on the reports page of our Django app by the end of the sprint (6 working days). How long, realistically?"

1. `Ask: add CSV export for the filtered report table. Done means: the Export button downloads a CSV matching the on-screen filter, covered by one test. Out: scheduled or emailed exports, Excel format, exports over 100k rows.` Row: defined (criteria agreed in the ticket), 0.5× to 2×.
2. `git ls-files reports/ | xargs wc -l | tail -1` prints `4,812 total`; `git grep -n 'ReportFilterSet' -- ':!*test*' | wc -l` prints `7`; `git grep -l 'ReportFilterSet' | wc -l` prints `5`, so `files=5`; tests grep prints `3`; owners: `41 m.kos`, `2 you`; 90-day commits `12`; migrations grep `0`. Hidden scope: tests `slice`, migration `out`, review wait `slice`, docs `out` (ticket says none), flag `slice` (reports page is customer-facing), monitoring `out`.
3. `gh pr list --state merged --limit 200 --search 'export' ...` with `-v f=5` keeps the PRs that touched 2 to 15 files and prints `n=6 median=3.4 p80=5.1`.
4. Slices: (1) streaming CSV view with the filter applied, O/M/P 0.5/1/2 days, done when `curl -s '/reports/export.csv?status=open' | head -2` shows the header and one row; (2) button behind the `reports_export` flag, 0.25/0.5/1, done when the button appears only with the flag on; (3) test for filter parity, 0.25/0.5/1, done when `pytest reports/tests/test_export.py` prints `1 passed`; (4) review wait, 1/2/3, done when merged. Unknown: "does `StreamingHttpResponse` play with the auth middleware", spike 2 hours, kept under `spikes/stream_auth.py`; resolved in 40 minutes, it does.
5. E = (0.5+4+2)/6 + (0.25+2+1)/6 + (0.25+2+1)/6 + (1+8+3)/6 = 1.08 + 0.54 + 0.54 + 2.0 = 4.2 days; low 2.0, high 7.0; row "sliced" after phase 4 (0.8× to 1.25×) gives 3.4 to 5.3, so low rises to 3.4; high stays 7.0 (wider than the row minimum). Reference median 3.4 is under E: no override. Block sent with `Range: 3.4–7 days, likely 4.2`, Assumptions: `m.kos reviews within 2 days (p80 5.1)`. response-self-review traces every number to a command line. Fits the sprint only if review lands by day 5: that sentence goes in the reply.
