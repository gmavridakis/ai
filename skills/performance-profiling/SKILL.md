---
name: performance-profiling
description: Measure before optimizing: baseline p50/p95, profile to the frame or query, change one thing, re-measure. Use when a request, page, job, build, or test suite is "slow", "takes forever", "got slower", a CPU or memory graph climbs, or an N+1 is suspected. Do not use when it fails or times out (error-triage), for one curl timing (api-debugging), or to keep duration lines (log-instrumentation).
---

# Performance Profiling

Slow code is fixed by guess far more often than by measurement: a cache is added to a handler whose time is in one unindexed query, a loop is micro-optimized while 90% of the wall time is a lock wait. This skill forces a number before any change and a profile before any hypothesis. The leading word is **baseline**: the measured number, with its conditions, that every later number is compared against.

Entry condition: the thing completes, only slowly. It fails, times out or returns an error: Call the Skill tool with "error-triage" first. One HTTP call whose split between DNS, TLS and server time is the question: Call the Skill tool with "api-debugging" (its `-w` timing line), then return with `ttfb` as the baseline. The `duration_ms` fields and timing lines added here that should stay in the code: Call the Skill tool with "log-instrumentation" once the fix is in.

## 1. Baseline: one metric, measured 3 times, before any change

Pick the metric the user feels, then measure it with the tool for its surface. Record p50 and p95 over at least 3 runs (10 for anything under 1 s), after a warm-up, with the dataset size, machine and build mode written next to the numbers.

| Surface | Command | Reads |
| --- | --- | --- |
| HTTP endpoint under load | `npx autocannon -c 10 -d 20 -H 'Authorization: Bearer <t>' <url>` (`k6 run` or `wrk -t2 -c10 -d20s` if installed) | `Latency` p50/p97.5/p99 and `Req/Sec` rows |
| One request, no load | `curl -s -o /dev/null -w 'ttfb=%{time_starttransfer} total=%{time_total}\n' <url>` 10 times in a loop | `ttfb` near `total` = the handler, far = the body size |
| CLI, script, build, test suite | `hyperfine --warmup 3 --runs 10 '<cmd>'` | `Time (mean ± σ)` and `Range (min … max)` |
| Web page | `npx lighthouse <url> --only-categories=performance --output=json --output-path=./lh.json --chrome-flags='--headless'` then `jq '.audits["largest-contentful-paint"].numericValue, .audits["interaction-to-next-paint"].numericValue, .audits["cumulative-layout-shift"].numericValue' lh.json` | LCP ms, INP ms, CLS |
| Mobile frame rate | Flutter: `flutter run --profile` with the `P` overlay; React Native: Perf Monitor; both in a release or profile build, never debug | frames over 16 ms (60 Hz) or 8 ms (120 Hz) |

Measurement is void when: Django `DEBUG=True` or the debug toolbar is on (it stores every query); a Flutter or React Native debug build; Node with `--inspect` attached; a laptop on battery; the first run (JIT, cold cache) is counted; or the dataset is 10 rows where prod has 10,000.

Noise band: the run-to-run spread of the baseline is the noise; a later change smaller than that spread, or under 10%, is not a result.

**Done when** a baseline table exists in the reply with p50, p95, run count, warm-up, dataset size, build mode and machine, and the user-felt metric is one of its rows.

## 2. Locate: CPU or wait, then the frame

A process at 100% CPU during the slow span is computing; one at under 30% is waiting (I/O, lock, GC pause, a downstream call). Check first, profile second: `top -p <pid>` or Task Manager during one slow run.

| Stack | Profile command | Open with | Gotcha |
| --- | --- | --- | --- |
| Node | `node --cpu-prof --cpu-prof-dir=./prof app.js`, then stop with SIGINT or `process.exit()`; `0x app.js` writes a flame graph HTML directly | `npx speedscope prof/CPU.*.cpuprofile` | the `.cpuprofile` is written at clean exit; `kill -9` or a crash leaves nothing. Default 1 ms samples; `--cpu-prof-interval 100` for a short run |
| Node memory | `node --heap-prof app.js` or `node --heapsnapshot-signal=SIGUSR2 app.js` and `kill -USR2 <pid>` twice, 1 minute apart | Chrome DevTools → Memory → load, *Comparison* view | a class whose `# Delta` only grows between snapshots is the leak |
| Python / Django | `py-spy record -o profile.svg --pid <pid> --duration 30` (add `--idle` to see wait, `--native` for C extensions); offline: `python -m cProfile -o out.prof manage.py <cmd>` | the SVG in a browser; `py-spy top --pid <pid>`; `snakeviz out.prof` | py-spy needs `sudo` or `CAP_SYS_PTRACE` on Linux (`Permission denied` or `Failed to open process`); under gunicorn attach to a worker pid, not the master |
| JVM | `asprof -e cpu -d 30 -f /tmp/cpu.html <pid>`; `-e wall` for waits, `-e alloc` for allocation, `-e lock` for contention. No agent install: `jcmd <pid> JFR.start duration=60s filename=/tmp/rec.jfr` then `jfr print --events jdk.ExecutionSample /tmp/rec.jfr` | the HTML; `jfr summary /tmp/rec.jfr` | `perf_event_open failed` or empty kernel frames: `sysctl kernel.perf_event_paranoid=1 kernel.kptr_restrict=0`; in a container `--cap-add SYS_ADMIN`; run with `-XX:+UnlockDiagnosticVMOptions -XX:+DebugNonSafepoints` for exact lines |
| Browser / React / Angular | Chrome DevTools → Performance → record one interaction; React DevTools Profiler → *Ranked* (react §Observation); `npx react-scan@latest <url>` | the Bottom-Up tab sorted by *Self Time* | a long task is over 50 ms; a commit over 16 ms is a dropped frame |
| Flutter / React Native | DevTools → Performance → *Enhance tracing* (flutter-dart §Observation); Perf Monitor and the DevTools Performance panel (react-native §Observation) | the frame chart | profile builds only |

Read a flame graph by width, not depth: the widest frame at the top of the stack (highest self time) is the first target; a frame under 5% is never worth a change. A wait profile (`-e wall`, `--idle`) whose top frames are `socketRead`, `recv`, `pthread_cond_wait`, `select` or a connection pool `getConnection` means the time is downstream: go to phase 3.

**Done when** the reply names the top 3 frames (function, file:line, self-time %) from one profile taken during the slow span, or states that the process waited and names what it waited on.

## 3. Count the queries and calls per operation

Most server-side waits are many small round trips, not one slow one. Count them for one operation; the count is the tell, the shape is the fix.

| Stack | Count | Tell |
| --- | --- | --- |
| Spring / Hibernate | `spring.jpa.properties.hibernate.generate_statistics=true` and `logging.level.org.hibernate.stat=DEBUG`; one request | `Session Metrics` line: `... JDBC statements` or `queries executed to database: <n>` with n close to the row count |
| Django | `from django.test.utils import CaptureQueriesContext` around the view, or `assertNumQueries(<n>)` in a test; `logging.getLogger('django.db.backends').setLevel(logging.DEBUG)` with `DEBUG=True` locally | the same `SELECT ... WHERE "app_x"."id" = %s` shape repeated once per row |
| Node (Prisma, Knex, pg) | `new PrismaClient({ log: ['query'] })`; Knex `debug: true`; `pg` through `log-instrumentation`'s `<dependency> call completed` DEBUG row | one `SELECT` per iteration of a `for` or `.map` over results |
| Any outbound HTTP | the DEBUG `<dependency> call completed` events of one request, counted with `jq -r 'select(.request_id=="<id>") | .target' /tmp/app.log | sort | uniq -c` | a target called more than 5 times for one request |

Thresholds: more than 10 statements for one read request, or a count that grows with the page size, is an N+1; a single statement over 100 ms is a missing index (`EXPLAIN ANALYZE <sql>` shows `Seq Scan` on a table over 10,000 rows). The fix is a stack row: in a Spring project Call the Skill tool with "java-spring-stack" (its N+1 row: `JOIN FETCH`, `@EntityGraph`, `@BatchSize`); in a Django project Call the Skill tool with "python-django" (its N+1 row: `select_related`, `prefetch_related`); in a Node service Call the Skill tool with "nodejs" (event-loop row; Prisma `include`, batching); a React render that re-fetches per row: Call the Skill tool with "react"; an Angular change-detection storm: Call the Skill tool with "angular"; a Flutter `build` over 16 ms: Call the Skill tool with "flutter-dart"; a React Native JS-thread frame drop: Call the Skill tool with "react-native".

**Done when** the statement or call count for one operation is a number in the reply, compared against the 10-statement and 100-ms thresholds, and the owning stack skill has been called for any count over threshold.

## 4. Change one thing, re-measure, keep or revert

One change per commit. Re-run the exact phase 1 command with the same conditions; the result is the p95 delta against the baseline, not the mean. A change inside the noise band is reverted (`git revert` or `git checkout -- <file>`) even if it "should" help. Stop when the user-felt metric is under its target or the next widest frame is under 5%.

```
| Metric | Baseline p50 / p95 | After p50 / p95 | Delta p95 | Change | Kept |
| --- | --- | --- | --- | --- | --- |
| <metric> | <n> / <n> ms | <n> / <n> ms | <-n%> | <one line> | yes / reverted (<reason>) |
```

**Done when** the table above is filled for every change tried, every row says kept or reverted, and the after measurement used the phase 1 command and conditions verbatim.

## Targets (Oct 2026)

| Metric | Target | Source |
| --- | --- | --- |
| LCP / INP / CLS | 2500 ms / 200 ms / 0.1 at p75 of field data | Core Web Vitals |
| Long task on the main thread | under 50 ms | Chrome DevTools |
| Frame (60 Hz / 120 Hz) | 16 ms / 8 ms | Flutter, React Native, React |
| Node event-loop lag | under 100 ms (nodejs row) | `perf_hooks.monitorEventLoopDelay` |
| JVM GC pause | under 200 ms at p99 (`-Xlog:gc*` or `jfr print --events jdk.GarbageCollection`) | G1 default pause goal |
| One SQL statement | under 100 ms; statements per read request under 10 | phase 3 |

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| "Added caching" or "made it async" with no before number | phase 1 baseline, then phase 2 profile |
| A micro-benchmark of a function with 2% self time | the widest frame |
| Mean of 1 run, or the first run after a restart | p95 over 3+ warm runs |
| Profiled the dev server, debug build or `DEBUG=True` | the void list of phase 1 |
| Index added to every column in the slow query | `EXPLAIN ANALYZE`, one index on the `Seq Scan` predicate |
| Three changes in one commit, "it is faster now" | one row per change in the phase 4 table |

## Example

**Ask:** "GET /api/orders got slow since last week, about 4 seconds for the dashboard. Spring Boot, Postgres."

1. Baseline: `npx autocannon -c 5 -d 20 -H 'Authorization: Bearer ...' http://localhost:8080/api/orders?page=0&size=50` three times after one warm-up run; p50 3,810 ms, p95 4,420 ms, 50 rows per page, local Postgres with the prod dump (120k orders), release jar, MacBook on power.
2. Locate: `top` shows the JVM at 12% CPU during the run, so it waits. `asprof -e wall -d 20 -f /tmp/wall.html <pid>`: top frames `SocketInputStream.socketRead0` 71%, `HikariPool.getConnection` 9%, `ObjectMapper.writeValue` 3%. Downstream: phase 3.
3. Count: `generate_statistics=true`, one request: `Session Metrics { ... 51 JDBC statements }` for 50 rows. N+1: Call the Skill tool with "java-spring-stack"; its row says `@EntityGraph(attributePaths = "customer")` on the repository method. The customer association was lazy; last week's change added `customer.name` to the DTO.
4. Re-measure with the same autocannon line: p50 142 ms, p95 210 ms, delta p95 -95%, 2 statements per request. Table row kept; next widest frame (`writeValue`, 3%) is under 5%, stop.
