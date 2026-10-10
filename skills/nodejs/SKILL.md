---
name: nodejs
description: Write, review, or fix Node.js code, or interpret a Node tell: ERR_REQUIRE_ESM, ERR_MODULE_NOT_FOUND, ERR_PACKAGE_PATH_NOT_EXPORTED, "__dirname is not defined", UnhandledPromiseRejection, MaxListenersExceededWarning, ERESOLVE, heap out of memory, event-loop lag, SIGTERM ignored. Use when package.json, .nvmrc, or .node-version is present and the code runs in Node. Do not use while the failing layer is unknown (error-triage first); UI code belongs to angular, react, react-native; backends to java-spring-stack, python-django.
---

# Node.js

Node failures are mostly module-system, version, and event-loop failures whose messages name the symptom, not the cause. *Pin* the runtime and module type first (the fix differs by major and by CJS/ESM), then match the *tell* against every row of the table before touching code. Writing or reviewing code: pin, then use the table's Fix column as the review checklist.

Entry: the failing layer is known to be code or data. A timeout, 4xx/5xx, or "works on their machine" with no layer yet: Call the Skill tool with "error-triage" first. Angular components, templates, or `NG`-coded errors in the same workspace: Call the Skill tool with "angular". React components, hooks, hydration, or a Next.js route in the same package: Call the Skill tool with "react". A `react-native` or `expo` dependency, Metro, or a native build: Call the Skill tool with "react-native". A Spring backend: Call the Skill tool with "java-spring-stack". A Django backend: Call the Skill tool with "python-django". Adding or reviewing log lines themselves (pino setup, which events, level, fields, request ID, redaction) rather than a Node tell: Call the Skill tool with "log-instrumentation".

## 1. Pin the runtime and module type (30 s, before any fix)

```sh
node -v; npm -v; cat .nvmrc .node-version 2>/dev/null; node -p "require('./package.json').engines"
node -p "require('./package.json').type || 'commonjs'"      # module system for .js files
node -p "require('./package.json').packageManager"          # if set, use that manager, not npm
ls package-lock.json pnpm-lock.yaml yarn.lock bun.lock* 2>/dev/null   # exactly one should exist
```

| Node line (Sep 2026) | Status | Consequence for fixes |
| --- | --- | --- |
| 20.x | EOL since 2026‑04‑30 | unpatched: the fix is an upgrade to 22 or 24; `require(esm)` only from 20.19; no type stripping |
| 22.x | Maintenance LTS until 2027‑04‑30 | `require(esm)` unflagged (22.12+), `node --run`, `--watch`, `--env-file`, `node:sqlite` (experimental); TS type stripping only from 22.18 |
| 24.x | Active LTS (maintenance from 2026‑10‑20, EOL 2028‑04‑30) | TS type stripping on by default (`.ts` runs directly, no enums/namespaces), `--permission` (was `--experimental-permission`), npm 11, `url.parse()` runtime‑deprecated, `URLPattern` global |
| 26.x | Current; LTS from 2026‑10 | last release of the odd/even model; 27 (Apr 2027) starts one‑major‑per‑year, every release LTS |

Propose fixes only from the pinned row (`import.meta.dirname` needs 20.11+, `--permission` needs 24, `require()` of an ESM package needs 22.12+). Mixed lockfiles: delete all but the one matching `packageManager` before any install.

**Done when** the Node major, the module type, the package manager, and the single lockfile are written down and one row of the table is chosen.

## 2. Match the tell: symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `ERR_REQUIRE_ESM` / `require() of ES Module … not supported` | CJS file `require()`s an ESM‑only package on Node < 22.12 / < 20.19 | 1. upgrade Node (22.12+ supports `require(esm)` unless the module has top‑level `await`); 2. `await import('pkg')`; 3. pin the last CJS major of the package. Converting the whole project to ESM is the last move, not the first |
| `ERR_MODULE_NOT_FOUND: Cannot find module '/…/utils'` (path exists as `utils.js` or `utils/index.js`) | ESM needs full relative specifiers | write `./utils.js` / `./utils/index.js`; in TS with type stripping the import must still end in `.ts` or `.js` |
| `ERR_PACKAGE_PATH_NOT_EXPORTED: Package subpath './lib/x' is not defined by "exports"` | deep import into a package that maps `exports` | `npm view pkg exports` → use a listed subpath; else ask upstream. Patching `node_modules` is not a fix |
| `ReferenceError: __dirname is not defined` / `require is not defined in ES module scope` | ESM file (`"type": "module"` or `.mjs`) using CJS globals | `import.meta.dirname` / `import.meta.filename` (20.11+); `createRequire(import.meta.url)` for a one‑off `require` |
| Process exits with `UnhandledPromiseRejection` / `[ERR_UNHANDLED_REJECTION]` | rejected promise nobody awaited (Node ≥ 15 crashes by default) | find it: `node --trace-uncaught --unhandled-rejections=strict app.js`; fix the missing `await`/`.catch`. Express 4: async handler rejections are swallowed; wrap with `express-async-errors` or upgrade to Express 5 (forwards them to error middleware). A global `unhandledRejection` handler that only logs hides the bug |
| `MaxListenersExceededWarning: Possible EventEmitter memory leak detected. 11 … listeners added` | a listener registered per request/loop iteration | `node --trace-warnings` prints the registering stack; move `.on()` out of the hot path or use `.once()`; raising `setMaxListeners` hides the leak |
| `FATAL ERROR: … JavaScript heap out of memory` | real leak, an unbounded array/Map/cache, or a default heap (~2–4 GB) too small for a legitimate dataset | `node --heapsnapshot-signal=SIGUSR2 app.js`, take two snapshots 5 min apart, compare Retained Size in Chrome DevTools → Memory; raise `NODE_OPTIONS=--max-old-space-size=<MB>` only when the retained set is legitimate |
| p99 latency spikes, `event loop lag` > 100 ms, requests time out while CPU is at 100 % | synchronous work on the loop (`JSON.parse` of MBs, `*Sync` fs/crypto calls, regex backtracking, big `for` over rows) | measure: `perf_hooks.monitorEventLoopDelay({resolution: 20})` → `h.percentiles.get(99)`; locate: `node --cpu-prof --cpu-prof-dir=./prof app.js`, open `.cpuprofile` in DevTools → Performance. Move the work to `worker_threads` or stream it; `setImmediate` chunking only for small loops |
| `npm ERR! code ERESOLVE … Could not resolve dependency: peer react@"^18"` | peer‑dependency conflict (npm 7+ enforces peers) | `npm ls <pkg>` to see who wants what; bump the outlier; `--legacy-peer-deps` only to unblock a spike, never committed to `.npmrc` |
| `npm ci` fails: `package.json and package-lock.json … are not in sync` | lockfile drift (edited `package.json` without `npm install`, or a different manager touched it) | `npm install --package-lock-only` locally, commit the lockfile; in CI always `npm ci`, never `npm install` |
| `gyp ERR! build error` / `node-pre-gyp … Pre-built binaries not found` | native addon has no prebuilt binary for this Node ABI/arch (`node -p process.versions.modules`, `process.arch`) | match the Node major the package publishes for (`npm view pkg engines`), or use a WASM/pure‑JS alternative (`bcryptjs` for `bcrypt`, `better-sqlite3`→`node:sqlite` on 22.5+) |
| Container takes 10 s to stop (`docker stop` hits its timeout), in‑flight requests dropped | `node` running as PID 1 does not forward SIGTERM; or no shutdown hook | `CMD ["node", "server.js"]` (exec form, not `npm start`) plus `docker run --init` / `tini`; `process.on('SIGTERM', () => server.close(() => process.exit(0)))` with a 10 s `setTimeout(() => process.exit(1)).unref()` |
| `ECONNRESET` / `socket hang up` on outbound calls after ~5 min idle | server closed a keep‑alive socket the client reused | prefer built‑in `fetch` (undici) with `AbortSignal.timeout(5_000)`; for `http.Agent` set `keepAlive: true, timeout` below the server's idle timeout; retry only idempotent methods |
| `Error [ERR_STREAM_PREMATURE_CLOSE]` / backpressure memory growth when copying files or piping HTTP | `.pipe()` chain without error propagation or `write()` ignoring `false` | `await pipeline(src, transform, dst)` from `node:stream/promises`; for manual writes honour `write()===false` → wait for `'drain'` |

No row matches the tell: Call the Skill tool with "debug-from-raw-logs" and bring the pinned versions with you. The complaint is "slow" with no tell and no number yet (no p95, no profile, no query count): Call the Skill tool with "performance-profiling" and return with its top frame or statement count.

**Done when** the tell matched one row, the row's fix was applied in its listed order, and the verbatim tell no longer appears when the failing command is re-run; or no row matched and debug-from-raw-logs was called.

## See what Node actually does

```sh
node --trace-warnings --trace-deprecation app.js         # stack for every warning/deprecation
node --unhandled-rejections=strict --trace-uncaught app.js
NODE_DEBUG=net,http,module node app.js                   # core module tracing (module = resolution)
node --print "require.resolve('pkg')"                     # which copy of pkg resolves from here
npm ls pkg; npm explain pkg                               # every path that pulls pkg into the tree
node --test --test-reporter=spec 'test/**/*.test.js'      # built-in runner; add --test-only, --watch
node --inspect-brk app.js  # then chrome://inspect        # breakpoint before first line
```

- Which env won: `node --env-file=.env -p "process.env.DB_URL"` (20.6+); `.env` never overrides an already‑set variable.
- Which module system a file gets: walk up from the file to the nearest `package.json` and read its `type`; `.mjs`/`.cjs` override it.
- Test one file with SQL/HTTP debug: `NODE_DEBUG=http node --test test/orders.test.js`.
- Prefer `node:` prefixed core imports (`import { readFile } from 'node:fs/promises'`): a bare `fs` can be shadowed by a package named `fs`.

## Example

User: "Our API on Node 22 randomly dies at night with `[ERR_UNHANDLED_REJECTION]`; logs show nothing before it."

1. Pin: `node -v` → 22.14.0; `type` → `commonjs`; Express 4.19 in `package.json` ⇒ row "Unhandled rejection", Express 4 clause.
2. Reproduce in staging with `node --unhandled-rejections=strict --trace-uncaught server.js`; the trace names `routes/report.js:41`: an `async (req, res)` handler whose `await db.query()` rejects on the 02:00 connection recycle; Express 4 never passes the rejection to the error middleware.
3. Fix: `npm install express@5` (handlers' rejected promises reach `app.use((err, req, res, next) => …)`), or if the upgrade is out of scope, `require('express-async-errors')` once at the top of `server.js`.
4. Keep the crash‑on‑unhandled default; add the SIGTERM hook from the table so the orchestrator restart is clean. Verify: run the failing query with the DB down → HTTP 500 from the error middleware, process still up, tell gone.
