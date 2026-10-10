---
name: log-instrumentation
description: Add or review logging: events, levels, fields, JSON output, request ID on every line, no secrets. Use when asked to "add logging", "log this", "logs are too noisy", "can't find the request in the logs", or when a new handler, job or outbound call has no log line at its boundary. Do not use to find a bug now (error-triage, debug-from-raw-logs) or to cap log output in context (context-hygiene).
---

# Log Instrumentation

Logs fail in two ways: nothing useful is there when the failure happens (no request ID, no boundary line, a secret in place of the field that mattered), or so much is there that the line that mattered is one of 40,000. Both come from logging sentences instead of *events*. An **event** is one log call with a constant message and named fields; the message answers "what happened", the fields answer "to which request, with what values, how long".

Entry condition: the user wants log lines that stay in the code. The question is where the time goes, not what happened: Call the Skill tool with "performance-profiling" (its phase 3 counts the `<dependency> call completed` events this skill emits). The user wants a bug found now: with the layer unknown Call the Skill tool with "error-triage"; with the layer known Call the Skill tool with "debug-from-raw-logs" (its phase 5 adds a temporary probe line; come back here if that line should stay). A tell from the logging library itself (`no applicable action for [encoder]`, `ERR_REQUIRE_ESM` loading `pino-pretty`, `ValueError: Unable to configure handler`) is a stack bug: in a Spring project Call the Skill tool with "java-spring-stack"; in a Node project Call the Skill tool with "nodejs"; in a Django project Call the Skill tool with "python-django". A component, hook, template or build error met while wiring the front-end `log.ts`: in an Angular workspace Call the Skill tool with "angular"; in a React or Next.js app Call the Skill tool with "react"; in a React Native or Expo app Call the Skill tool with "react-native"; in a Flutter app Call the Skill tool with "flutter-dart".

## 1. Pin the logger, the format and the request ID (config, not call sites)

| Stack | Logger | JSON output | Request ID on every line |
| --- | --- | --- | --- |
| Spring Boot 3.4+ | `LoggerFactory.getLogger(Cls.class)` (SLF4J 2) | `logging.structured.format.console=ecs` (`logstash`, `gelf` also built in, no dependency) | `micrometer-tracing-bridge-otel` fills `traceId`/`spanId` via `logging.pattern.correlation`; own ID: `MDC.put("request_id", id)` in a `OncePerRequestFilter`, `MDC.clear()` in `finally` |
| Spring Boot 2.x / 3.0 to 3.3 | same | `logstash-logback-encoder` with `<encoder class="net.logstash.logback.encoder.LogstashEncoder"/>` in `logback-spring.xml` | MDC as above |
| Node | `pino` (ndjson by default), `pino-http` for the access line | `pino-pretty` only through `transport` in dev; never in prod | `pino-http` sets `req.id` from `x-request-id` or `genReqId`; log through `req.log` (a child with `reqId`) |
| Django / Python | `logging.getLogger(__name__)` or `structlog.get_logger()` | `pythonjsonlogger.json.JsonFormatter` (python-json-logger 3.x) in `LOGGING["formatters"]`, or `structlog.processors.JSONRenderer()` | `django-structlog` middleware binds `request_id`; stdlib: a `contextvars.ContextVar` read by a `logging.Filter` that sets `record.request_id` |
| Angular / React / React Native | one `log.ts` wrapping `console` with `level` and `event`, no library | console (JSON on `console.info(JSON.stringify(...))` only when shipped to a collector) | the `x-request-id` of the failing response, logged with the error |

One format per process: a prod process printing both JSON and `pino-pretty` or `%d %-5level` text lines has two configs; keep the JSON one.

**Done when** the logger, the format line and the request-ID mechanism for the stack are in one config file (not repeated at call sites) and `<run> 2>&1 | head -1 | jq .` parses.

## 2. Choose the events and their level

Log at boundaries; inside a boundary, log nothing above DEBUG. Match every new or reviewed call site against a row:

| Boundary | Message (constant) | Level | Fields |
| --- | --- | --- | --- |
| HTTP request handled | `request completed` by the framework's access middleware (`pino-http`, Spring `CommonsRequestLoggingFilter` or the gateway, `django.server` / `django.request`), never by hand | INFO; ERROR when status >= 500 | `method`, `route` (template `/orders/{id}`, not the raw URL), `status`, `duration_ms` |
| Outbound call: HTTP, SQL batch, queue publish | `<dependency> call completed` | DEBUG; INFO when `duration_ms` > 1000 or it failed | `target`, `op`, `status`, `duration_ms`, `attempt` |
| Job, consumer, scheduled task | `job started`, `job finished` | INFO (two lines per run, not one per item) | `job`, `items`, `failed`, `duration_ms` |
| Business state transition | `<entity> <state> changed` (`order status changed`) | INFO | `<entity>_id`, `from`, `to`, `actor` |
| Retry, fallback, dropped item, deprecated path | `retrying`, `fallback used`, `message dropped` | WARN | `reason`, `attempt`, `max_attempts` |
| Exception that ends the operation | `<operation> failed` | ERROR, once, at the catch site that handles it | `error.type`, `error.message`, stack: `exc_info=True`, `log.error("...", e)` (throwable last), `{ err }` in pino |
| Per item inside a loop | nothing at INFO | DEBUG, or one summary line with counts after the loop | `count`, `failed` |

Level rule: ERROR means someone must act and it pages; WARN means degraded but handled; INFO tells the story of one request in at most 4 lines (the access line plus at most 3 own events); DEBUG is off in prod and switched on per logger (`logging.level.com.acme.orders=DEBUG`, `LOG_LEVEL=debug` with `pino({ level: process.env.LOG_LEVEL })`, `LOGGING["loggers"]["orders"]["level"]`); TRACE carries payload bodies and is never on by default.

Budget: more than 4 INFO events on one request path, lower the extra ones to DEBUG or fold them into fields of the boundary event. A loop over more than 100 items logs one summary line, or samples 1 in 100 (`if (i % 100 === 0)`).

**Done when** every new or reviewed call site is one row (boundary, message, level, fields) listed in the reply, and the INFO count per request path is written down and at most 4.

## 3. Shape each event

- Constant message, values in fields: `log.info("order shipped", kv("order_id", id), kv("carrier", c))` (`net.logstash.logback.argument.StructuredArguments.kv`), or SLF4J 2 fluent `log.atInfo().addKeyValue("order_id", id).log("order shipped")`; Node `req.log.info({ orderId, carrier }, 'order shipped')`; Python `log.info("order shipped", extra={"order_id": id, "carrier": c})` or structlog `log.info("order_shipped", order_id=id)`. A value inside the message (`f"order {id} shipped"`, `"order " + id`) cannot be grouped or counted.
- Field names: one casing per process, the access line's casing wins (`request_id` in Python and ECS, `reqId` in pino); ids as strings; durations as integer `duration_ms`; sizes as `bytes`; never `data`, `obj`, `info` as a field name.
- Placeholders, not concatenation: `log.debug("row {}", row)` not `"row " + row`; Java and Python evaluate the concatenation (and `toString()`) even when DEBUG is off.
- One exception, one line: the catch site that handles it logs ERROR with the stack; every site that rethrows logs nothing. The tell of a violation: the same stack trace twice, two timestamps.
- Secrets out by config, not by memory: pino `redact: { paths: ['req.headers.authorization', 'req.headers.cookie', '*.password', '*.token'], censor: '[Redacted]' }`; Logback `logstash-logback-encoder` `<jsonGeneratorDecorator class="net.logstash.logback.mask.MaskingJsonGeneratorDecorator"><defaultMask>***</defaultMask><path>password</path><path>authorization</path></jsonGeneratorDecorator>`; Python a `logging.Filter` that replaces those keys on `record.__dict__`. Then check the call sites: `grep -rnE '(log|logger)\.\w+\(.*(password|passwd|secret|token|authorization|cookie|iban|card)' src/` must return 0 lines, or only lines that name the field and log its length or last 4 characters.
- Request and response bodies: never at INFO. Log `bytes` and `content_type`; the body only at TRACE behind the per-logger switch of phase 2.

**Done when** no message string contains an interpolated business value (`grep -rnE '(log|logger)\.\w+\((f"|".*" \+)' src/` returns 0 lines or only constant strings) and the secret grep returns 0 lines.

## 4. Verify on one run

Run one request or one job with output to a file (`<run> > /tmp/app.log 2>&1`), then read it by ID, not by scrolling; a file over 100 lines: Call the Skill tool with "context-hygiene" before reading it.

```sh
jq -c 'select(.request_id=="<id>") | {level, message, duration_ms}' /tmp/app.log   # the story of one request, in order
jq -r '.level' /tmp/app.log | sort | uniq -c                                         # per-level counts
jq -r 'keys[]' /tmp/app.log | sort | uniq -c | sort -rn | head -20                   # field names: two spellings of one field is a bug
grep -c '^[^{]' /tmp/app.log                                                         # non-JSON lines (a second config, a print, a library writing to stdout)
```

Thresholds: a healthy run has 0 ERROR lines; one request has at most 4 INFO lines; one message repeated more than 100 times per minute is noise (DEBUG or sample it); `grep -c '^[^{]'` above 0 in prod config means a stray `print`/`console.log` or a second formatter.

**Done when** the first jq command prints the request's events in order, the per-level count table and the non-JSON count are in the reply, and 0 ERROR lines appeared on the healthy run.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| `log.info("Processing...")`, `"Done"`, `"here 2"` (no noun, no fields; thousands of identical lines) | a boundary row from phase 2 with fields, or delete |
| `print(...)` / `console.log(...)` in a server (no level, no JSON, no request ID) | the stack's logger from phase 1 |
| `except Exception: log.error(...)` then continue | re-raise, or WARN `fallback used` with `reason` |
| `log.error(e.getMessage())` without the throwable | `log.error("<operation> failed", e)` so the stack is in the line |
| A log line per item in a batch of 10,000 | one `job finished` line with `items` and `failed` |
| `log.info("user logged in", extra={"user": user})` (whole object: PII, password hash, 2 KB) | `user_id` only |

## Example

**Ask:** "Shipments fail in prod a few times a day and we find nothing in the logs. Add logging to the Spring order service."

1. Pin: Boot 3.5, Logback text pattern, no request ID. Add `logging.structured.format.console=ecs` and a `OncePerRequestFilter` that reads `X-Request-Id` (or a UUID) into `MDC.put("request_id", id)`. `./mvnw -q spring-boot:run 2>&1 | head -1 | jq .` parses.
2. Events: `POST /orders/{id}/ship` has 0 own events. Add `order status changed` (INFO: `order_id`, `from`, `to`), `carrier call completed` (DEBUG, INFO over 1000 ms or failed: `target`, `status`, `duration_ms`, `attempt`), `ship order failed` (ERROR with the throwable at the controller advice, where the 500 is produced). INFO per request: access line + 1 = 2.
3. Shape: `log.atInfo().addKeyValue("order_id", id).addKeyValue("from", old).addKeyValue("to", "SHIPPED").log("order status changed")`. The carrier client logged the full request body at INFO including the API key; moved to TRACE and the key masked by `MaskingJsonGeneratorDecorator`. Secret grep: 0 lines.
4. Verify: one shipment with `curl -H 'X-Request-Id: test-1'`; `jq -c 'select(.request_id=="test-1")'` prints 3 lines (status changed, carrier 412 ms, request completed 201). Levels: INFO 3, no ERROR, non-JSON 0. The next prod failure is one `jq` by request ID away: `ship order failed` with the carrier's `status` and the stack.
