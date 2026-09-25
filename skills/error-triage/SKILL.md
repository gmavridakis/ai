---
name: error-triage
description: Classify an error by the layer it comes from (network, auth, config, code, data) and run the single fastest diagnostic for that layer before anything else. Use when a user pastes an error message, status code, or "it fails" report and the cause is not yet known — especially for errors that could plausibly come from several layers (timeouts, 4xx/5xx, "connection refused", "permission denied", "invalid value"). Do not use once the failing layer is already established; hand off to debug-from-raw-logs for deep investigation of a known-layer bug.
---

# Error Triage

Most time lost on errors is spent debugging the wrong layer: reading application code for what is a DNS failure, or rotating credentials for what is a typo in a config key. Triage first: decide *which layer* is failing, confirm it with one cheap check, then go deep.

## 1. Capture the literal error (2 minutes, no interpretation)

- Get the exact text: error type, message, status code, exit code, and the first line of the stack trace. Ask for a copy-paste, not a paraphrase.
- Note **where** it surfaced: client, server, CI, proxy, browser console, a log file. The reporter of the error is often not the origin.
- Note **when** it started: always / since a deploy / since a config change / intermittently. "Intermittent" almost always means network, capacity, or a race — not a logic bug.

## 2. Classify by layer using the signature

Match the error against the table. Pick the first layer whose signature fits; if two fit, test the one that is cheaper to check.

| Layer | Typical signatures | Fastest diagnostic |
| --- | --- | --- |
| **Network** | `ECONNREFUSED`, `ETIMEDOUT`, `ENOTFOUND`, `getaddrinfo`, `connection reset`, `502/503/504`, TLS handshake / certificate errors, works from one machine but not another | `curl -sv <url>` (or `nc -zv host port`) from the failing host. Separates DNS, TCP, TLS, and HTTP in one output. |
| **Auth** | `401`, `403`, `Unauthorized`, `Forbidden`, `invalid token`, `signature expired`, `access denied`, works for one user/key but not another | Repeat the exact request with a known-good credential (`curl -H "Authorization: ..."`). If it passes, the credential is wrong/expired/under-scoped; if it still fails, it is not auth. |
| **Config** | `undefined is not a function` on a client object, `KeyError: 'DATABASE_URL'`, `null` where a setting should be, wrong host/port/region, behaves differently per environment | Print the effective config at startup (`env \| grep PREFIX`, `--print-config`, a one-line log). Compare the failing env's values to a working env's. |
| **Code** | `TypeError`, `NullPointerException`, `IndexError`, assertion failures, a stack trace with frames in your own source, reproducible with the same input every time | Re-run the smallest failing unit (one test, one function call) with the same input locally. Deterministic + own-code frame ⇒ code. |
| **Data** | `ValidationError`, `UNIQUE constraint failed`, `invalid JSON`, `unexpected token`, encoding errors, fails only for *some* records/inputs | Isolate the one failing record (`head`/`jq`/`SELECT ... LIMIT 1`) and run it alone. Fails alone ⇒ data; passes alone ⇒ look at ordering/state instead. |

Rules of thumb:

- A `500` with no body is *their* code; a `500` with a stack trace naming your service is *your* code.
- "Works locally, fails in CI/prod" is config or network until proven otherwise.
- "Works for me, fails for them" is auth or data until proven otherwise.
- The first error in a log is the cause; later errors are fallout. Triage the first one.

## 3. Run exactly one diagnostic, then reclassify

- Run the fastest diagnostic for the chosen layer and read its output literally.
- If it confirms the layer, stop triaging and fix (or hand off to `debug-from-raw-logs` if the cause is still unclear within that layer).
- If it rules the layer out, move to the next best-fitting layer. Do not run diagnostics for three layers at once; results become impossible to attribute.
- Write down each ruled-out layer and the evidence that ruled it out. This prevents circling back.

## 4. Report the triage

State, in this order: the layer, the evidence that pinned it, the next action. One line each.

> Layer: auth. Evidence: same request with a fresh token returns 200; the failing token's `exp` claim is yesterday. Next: rotate the token in the deploy secret.

## Anti-patterns to refuse

- Opening the application code before checking whether the request even reached the application.
- Regenerating credentials when the error is `ENOTFOUND` (DNS), or restarting the service when the error is `403`.
- Treating a `504` from a load balancer as a bug in the handler; check upstream timeouts and health checks first.
- Declaring "flaky test" without a layer; flakiness has a layer too (usually network or shared state).

## Example

**Report:** "The checkout API returns 502 since this morning, only in production."

1. Capture: `502 Bad Gateway`, returned by the ALB, body empty, started 08:10 after nothing was deployed.
2. Classify: `502` + empty body + no deploy ⇒ network layer (gateway cannot reach upstream), not code.
3. Diagnostic: `curl -sv http://checkout-svc:8080/health` from inside the VPC ⇒ `connection refused`. Service process is down, gateway is fine.
4. Reclassify: process crash ⇒ check the service's own logs; the first error is `OOMKilled` at 08:09 ⇒ capacity/config, not the handler code.
5. Report: Layer: config (memory limit). Evidence: pod OOMKilled at 08:09, ALB 502s start 08:10. Next: raise the limit and find the allocation growth in a follow-up.
