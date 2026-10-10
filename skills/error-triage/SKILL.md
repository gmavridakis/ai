---
name: error-triage
description: Classify an error by failing layer (network, auth, config, code, data) and run one diagnostic to confirm it. Use when an error, status code, or "it fails" report has unknown cause: timeouts, 4xx/5xx, "connection refused", "permission denied". Do not use once the layer is known: java-spring-stack, nodejs, python-django, angular, flutter-dart, react, react-native, api-debugging (request in hand) or debug-from-raw-logs owns it; wrong 200 content: structured-prompting.
---

# Error Triage

Most time lost on errors is spent in the wrong *layer*: reading application code for a DNS failure, rotating credentials for a typo in a config key. Decide which layer fails, confirm it with one check, then hand off.

## 1. Capture the literal error (2 minutes, no interpretation)

- Get the exact text: error type, message, status code, exit code, and the first line of the stack trace. Ask for a copy-paste, not a paraphrase.
- Note **where** it surfaced: client, server, CI, proxy, browser console, a log file. The reporter of the error is often not the origin.
- Note **when** it started: always / since a deploy / since a config change / intermittently. "Intermittent" almost always means network, capacity, or a race, not a logic bug.

**Done when** three lines are written down: the verbatim first error line, where it surfaced, when it started.

## 2. Classify by layer using the signature

Match the error against every row. Pick the first layer whose signature fits; if two fit, take the one that is cheaper to check.

| Layer | Typical signatures | Fastest diagnostic |
| --- | --- | --- |
| **Network** | `ECONNREFUSED`, `ETIMEDOUT`, `ENOTFOUND`, `getaddrinfo`, `connection reset`, `502/503/504`, TLS handshake / certificate errors, works from one machine but not another | `curl -sv <url>` (or `nc -zv host port`) from the failing host. Separates DNS, TCP, TLS, and HTTP in one output. |
| **Auth** | `401`, `403`, `Unauthorized`, `Forbidden`, `invalid token`, `signature expired`, `access denied`, works for one user/key but not another | Repeat the exact request with a known-good credential (`curl -H "Authorization: ..."`). Passes: the credential is wrong, expired, or under-scoped. Still fails: it is not auth. |
| **Config** | `undefined is not a function` on a client object, `KeyError: 'DATABASE_URL'`, `null` where a setting should be, wrong host/port/region, behaves differently per environment | Print the effective config at startup (`env \| grep PREFIX`, `--print-config`, a one-line log). Compare the failing env's values to a working env's. |
| **Code** | `TypeError`, `NullPointerException`, `IndexError`, assertion failures, a stack trace with frames in your own source, reproducible with the same input every time | Re-run the smallest failing unit (one test, one function call) with the same input locally. Deterministic + own-code frame ⇒ code. |
| **Data** | `ValidationError`, `UNIQUE constraint failed`, `invalid JSON`, `unexpected token`, encoding errors, fails only for *some* records/inputs | Isolate the one failing record (`head`/`jq`/`SELECT ... LIMIT 1`) and run it alone. Fails alone ⇒ data; passes alone ⇒ look at ordering/state instead. |

Rules of thumb:

- A `500` with no body is *their* code; a `500` with a stack trace naming your service is *your* code.
- "Works locally, fails in CI/prod" is config or network until proven otherwise.
- "Works for me, fails for them" is auth or data until proven otherwise.
- The first error in a log is the cause; later errors are fallout. Triage the first one.

**Done when** one layer is named and its diagnostic is written out as a runnable command with the real host, URL, credential placeholder, or record filled in.

## 3. Run exactly one diagnostic, then reclassify

- Run the diagnostic for the chosen layer and read its output literally.
- Confirmed: stop triaging and go to step 4.
- Ruled out: write down the layer and the evidence that ruled it out, pick the next best-fitting layer, repeat. One diagnostic at a time; three layers at once give results nobody can attribute.

**Done when** one layer is confirmed by the diagnostic's own output, and every layer tried before it has a one-line ruling-out note.

## 4. Report the verdict and hand off

Three lines, in this order:

```
Layer: <network|auth|config|code|data>. Evidence: <the diagnostic output that pinned it>. Next: <one action>.
```

> Layer: auth. Evidence: same request with a fresh token returns 200; the failing token's `exp` claim is yesterday. Next: rotate the token in the deploy secret.

When the diagnostic already shows the fix, apply it. Otherwise hand the confirmed layer to the owner:

- Code or data layer in a Spring project (`pom.xml` or `build.gradle` names `org.springframework.boot`): Call the Skill tool with "java-spring-stack".
- Code or data layer with a `package.json` whose code runs in Node: Call the Skill tool with "nodejs".
- Code or data layer with `manage.py`: Call the Skill tool with "python-django".
- Code layer with `angular.json`: Call the Skill tool with "angular".
- Code layer with a `pubspec.yaml` that lists a `flutter` sdk dependency: Call the Skill tool with "flutter-dart".
- Code layer with a `package.json` that lists `react-dom` or `next` (hooks, components, hydration, Server Components): Call the Skill tool with "react".
- Code layer with a `package.json` that lists `react-native` or `expo` (Metro, red box, native module, Xcode or Gradle build): Call the Skill tool with "react-native".
- Network or auth layer on one HTTP endpoint the user can call, with the request in hand (a client, a Postman control, a curl): Call the Skill tool with "api-debugging".
- Any other layer or stack: Call the Skill tool with "debug-from-raw-logs".
- No failure at all: the response is a 200, the job or build finishes, and the report is only "slow": there is no layer to classify. Call the Skill tool with "performance-profiling".
- An LLM call that returned 200 with the wrong shape or content: Call the Skill tool with "structured-prompting".
- The confirmed layer is inside a vendor service or a third-party package the team cannot change, and the user wants it reported: Call the Skill tool with "bug-report-writing" with the verdict as its *Actual* field.
- Whichever layer: the service's own logs had no line for the failing request (no request ID, no boundary event), so the diagnostic ran blind. Add that gap to *Next* and, after the hand-off above, Call the Skill tool with "log-instrumentation".

**Done when** the three-line verdict is in the reply and exactly one of the above has happened: the fix applied, or one skill called.

## Anti-patterns to refuse

- Opening the application code before checking whether the request even reached the application.
- Regenerating credentials when the error is `ENOTFOUND` (DNS), or restarting the service when the error is `403`.
- Treating a `504` from a load balancer as a bug in the handler; check upstream timeouts and health checks first.
- Declaring "flaky test" without a layer; flakiness has a layer too (usually network or shared state).

## Example

**Report:** "The checkout API returns 502 since this morning, only in production."

1. Capture: `502 Bad Gateway`, returned by the ALB, body empty, started 08:10 after nothing was deployed.
2. Classify: `502` + empty body + no deploy ⇒ network layer (gateway cannot reach upstream), not code. Diagnostic: `curl -sv http://checkout-svc:8080/health` from inside the VPC.
3. Run it ⇒ `connection refused`. Service process is down, gateway is fine. Reclassify: process crash ⇒ read the service's own logs; the first error is `OOMKilled` at 08:09 ⇒ config (memory limit), not the handler code.
4. Verdict: `Layer: config (memory limit). Evidence: pod OOMKilled at 08:09, ALB 502s start 08:10. Next: raise the limit, then find the allocation growth.` The growth is a known-layer code bug in a Spring service: Call the Skill tool with "java-spring-stack".
