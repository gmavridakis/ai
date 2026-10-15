---
name: incident-response
description: Run a production incident: declare severity, mitigate before diagnosing, update on a cadence, then root-cause and write the postmortem. Use when users are affected now: "the site is down", "prod is broken", a page or alert fired, error rate or latency jumped after a deploy, "we need a postmortem". Do not use for one failing call with no user impact (error-triage), a runbook (documentation-writing), or an upstream report (bug-report-writing).
---

# Incident Response

An incident is lost in its first 20 minutes: the responder opens the code to find the cause while users keep failing, nobody says what is known, and the deploy that caused it stays live. This skill sizes the impact, stops the bleeding with the smallest reversible action, keeps a written cadence, and only then finds the cause and records what to change. The leading word is **mitigate**: the action that returns users to service before anyone knows why.

Entry: users or a paying system are failing now, or an alert fired. One error, one user, or a failing test with no impact graph: Call the Skill tool with "error-triage". The user wants a runbook or how-to for next time, not this incident: Call the Skill tool with "documentation-writing".

## 1. Declare and size (first 5 minutes)

Open a channel (`#inc-<yyyymmdd>-<slug>`) or thread, name one incident commander (IC: coordinates and communicates, does not debug), and pick the severity from the impact, never from the loudness of the report. Measure the impact with one query before choosing the row: error rate (`sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`), p95 latency, or a count from the logs (`grep -c ' 5[0-9][0-9] ' access.log` on the last 5 minutes).

| Row | Impact right now | First update by | Cadence | Who is told |
| --- | --- | --- | --- | --- |
| SEV1 | all users or a revenue, login or payment path down; error rate over 20%; data being lost or exposed | 5 min | every 30 min | leadership, support, status page, customers |
| SEV2 | one feature or region down, or error rate 5–20%, or p95 over 3× baseline; a workaround exists | 15 min | every 60 min | support, product, status page if customer-visible |
| SEV3 | degraded for some users, under 5% errors, no workaround needed | 60 min | at resolution | the owning team |
| SEV4 | no user sees it yet (disk at 85%, cert expires in 3 days, a queue growing) | next working day | at resolution | the owning team, as a ticket |

Post the first message with the template below, blank fields written as `unknown`. A severity is lowered only with the measurement that justifies it; raising it needs none.

**Done when** the channel exists, the IC is named in it, and the first update is posted with a severity row and an impact number from a query, inside the row's first-update window.

## 2. Mitigate before diagnosing

Ask only "what changed" and "what reverses it", not "why". List the changes in the last 24 hours, newest first, and take the first row whose time matches the start of the impact:

| What changed | Find it | Reverse it | Proof |
| --- | --- | --- | --- |
| Deploy | `kubectl rollout history deployment/<name>` · `gh run list --limit 10 --workflow deploy.yml` · `git log --since=24.hours --first-parent --format='%h %ad %s' --date=iso` | `kubectl rollout undo deployment/<name> --to-revision=<n>` · `git revert -m 1 <merge-sha>` then deploy · `vercel rollback <deployment-url>` · `heroku releases:rollback v<n>` | `kubectl rollout status deployment/<name> --timeout=120s` prints `successfully rolled out` |
| Feature flag or config | the flag audit log; `kubectl get configmap <name> -o yaml \| grep -n <key>`; `git log -p --since=24.hours -- '*.env*' 'config/'` | flip the flag off; `kubectl rollout restart deployment/<name>` after a ConfigMap revert | the flag reads off in the admin UI and one request with the old path succeeds |
| Traffic (spike, one client, a crawler) | `awk '{print $1}' access.log \| sort \| uniq -c \| sort -rn \| head` · the WAF or CDN top-IPs panel | rate-limit or block that client at the edge; `kubectl scale deployment/<name> --replicas=<2× current>` | the top IP drops out of the head of the list; error rate falls on the graph |
| Dependency (database, queue, vendor API) | `SELECT pid, now()-query_start AS age, state, left(query,80) FROM pg_stat_activity WHERE state <> 'idle' ORDER BY age DESC LIMIT 10;` · the vendor status page · `curl -s -o /dev/null -w '%{http_code} %{time_total}\n' <vendor-url>` | `SELECT pg_cancel_backend(<pid>);` (then `pg_terminate_backend` if still running) · fail over to the replica · switch the vendor call to its fallback or a cached response | the age column no longer shows minutes; the vendor probe returns `200` under 1 s |
| Capacity (OOM, disk, connections) | `kubectl get events --sort-by=.lastTimestamp \| grep -i -E 'OOMKilled\|Evicted\|FailedScheduling'` · `df -h` · `SELECT count(*) FROM pg_stat_activity;` | raise the limit or add replicas; delete rotated logs, not data; raise the pool cap one notch | no new `OOMKilled` event in 10 minutes; `df -h` under 80% |

Mitigation rules: one action at a time, each posted in the channel before it runs (`Trying: <command>; expect: <observable>`); the rollback of the newest deploy is always the first candidate when the timing matches; a fix-forward is allowed only when the revert itself is unsafe (a migration ran, a schema changed) and then the IC says so in the update. Keep every command and its first output line; they become the timeline.

**Done when** the impact metric from phase 1 has stayed under the next lower severity row for 10 minutes and the update says which action did it, with the command and its proof line pasted.

## 3. Communicate on the cadence

Every update, including "no change", uses the same shape; the IC posts it at the row's cadence even while the responders are busy:

```
[SEV<n>] <service>: <one-line impact in user terms>
Status: investigating | mitigating | monitoring | resolved
Impact: <who, since hh:mm UTC, <metric> at <value>>
Cause: <unknown | suspected: <change>>
Action: <what is running now, by whom>
Next update: <hh:mm UTC>
```

The external line (status page, support macro) is the first line plus `Next update:` and nothing from `Cause:` until the postmortem is published. A hand-over names the new IC and reposts the latest update in full. A SEV1 or SEV2 longer than 2 hours gets a second person whose only job is the updates.

**Done when** every update since the first is at most one cadence interval apart, and a `Status: resolved` update names the mitigation and the time the metric recovered.

## 4. Root-cause after stability

Only in `monitoring` status, with the cadence still running. Build the timeline first from the artefacts phase 2 kept (`<hh:mm> <event or command> <first output line>`): detection, first update, each action, recovery. Then find the cause by its layer: the failing layer is unknown: Call the Skill tool with "error-triage" with the timeline as its *when it started* line. The layer is known and the fix would otherwise be guessed: Call the Skill tool with "debug-from-raw-logs" with the red command from the incident window. One vendor endpoint misbehaved: Call the Skill tool with "api-debugging" with the request ID from the incident window. The cause is in a package or vendor the team cannot change: Call the Skill tool with "bug-report-writing" with the timeline as the repro. The permanent fix is its own PR, separate from the mitigation, and ships through the normal pipeline; the mitigation stays until the fix is deployed and the metric is checked again.

**Done when** the timeline has a timestamped line per action, the cause is one sentence with its evidence (a log line, a diff, a query result), and the permanent fix is merged or has a ticket number in the channel.

## 5. Postmortem within 5 working days

Blameless: name actions and systems, not people ("the deploy at 14:02 removed the index", never "<name> forgot"). Write `docs/postmortems/<yyyy-mm-dd>-<slug>.md`:

 ```markdown
 # <yyyy-mm-dd> <service>: <one-line impact>
 Severity: SEV<n> · Duration: <hh:mm> (<start> to <recovery> UTC) · Impact: <users or requests affected, number>
 TTD <min> (first symptom to declared) · TTM <min> (declared to mitigated) · TTR <min> (declared to resolved)
 ## Timeline (UTC)
 - <hh:mm> <event, command or decision>
 ## Root cause
 <one paragraph: the change, why it broke, why it was not caught>
 ## Contributing factors
 - <missing alert, test gap, no runbook, single owner>
 ## What went well / what hurt
 ## Action items
 | Item | Type | Owner | Due | Ticket |
 | --- | --- | --- | --- | --- |
 | <fix or guard> | prevent · detect · mitigate faster | <name> | <date> | <id> |
 ```

Each action item has one owner and a date; "be more careful" is not an item. At least one `detect` item exists when TTD exceeds 10 minutes; a missing log line or request ID is that item: Call the Skill tool with "log-instrumentation". A runbook update or a new runbook for the alert: Call the Skill tool with "documentation-writing" with the `Reader:` line `on-call engineer, arrives with "<alert>", leaves able to <the phase 2 action>`.

**Done when** the file exists at that path with every heading filled, TTD, TTM and TTR computed from the timeline, and every action item row has an owner, a date and a ticket.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| Reading source code while the error rate is above the row | the phase 2 table; the cause waits for `monitoring` |
| "Deploying a quick fix" during the incident | `rollout undo` or the flag; fix-forward only when the revert is unsafe, said in the update |
| Two mitigations started at once | one `Trying:` line, its proof, then the next |
| Silence because nothing changed | the update shape with `Status:` unchanged, on the cadence |
| A postmortem that names a person | the action or system at that timestamp |
| Action items without owner and date | the table row; untaken items are deleted, not carried |

## Example

**Ask:** "Checkout is throwing 502s since about 14:05, support is getting tickets, we deployed something around 14:00. What do we do?"

1. `#inc-20261015-checkout-502` opened, IC named. Query: error rate `0.34` over 5 min on `checkout-api`. Row SEV1 (payment path, over 20%). First update at 14:09: `[SEV1] checkout-api: checkout fails for every user since 14:05 UTC. Status: investigating. Impact: all customers, 5xx at 34%. Cause: unknown. Action: listing deploys. Next update: 14:39.`
2. `kubectl rollout history deployment/checkout-api` shows revision 48 at 14:01. `Trying: kubectl rollout undo deployment/checkout-api --to-revision=47; expect: 5xx under 5%.` Status line: `deployment "checkout-api" successfully rolled out` at 14:13. Rate `0.02` at 14:16, `0.01` at 14:23. Status moves to `monitoring`.
3. Updates at 14:09, 14:39 (`monitoring`, mitigation named), 15:09 (`resolved`, metric recovered at 14:16). Status page carried only the first line and the next-update time.
4. Timeline built from the channel. Layer unknown: Call the Skill tool with "error-triage"; verdict `Layer: config`, revision 48 shipped a `DB_POOL_SIZE=5` in the Spring profile against 20 pods. Fix PR raises it to 20 with a startup assertion; merged 16:40, deployed after the metric held.
5. `docs/postmortems/2026-10-15-checkout-502.md`: TTD 4 min, TTM 11 min, TTR 64 min. Action items: `prevent` (config value asserted at startup, owner, due in 1 week), `detect` (alert on 5xx over 5% for 2 minutes; the page came from support, so Call the Skill tool with "log-instrumentation" for the pool-exhaustion event), runbook `docs/runbooks/checkout-5xx.md` via documentation-writing.
