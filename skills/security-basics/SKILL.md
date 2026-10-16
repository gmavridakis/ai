---
name: security-basics
description: Review or harden code on four basics: secrets in source or git history, input validation and injection at each boundary, least privilege for containers, database users, CI and CORS, and a dependency audit. Use for "security review", "is this safe", "audit dependencies", "I committed a key", a gitleaks, npm audit or `CVE-` finding. Do not use for a version conflict (dependency-troubleshooting), secrets in logs (log-instrumentation), or users exposed now (incident-response).
---

# Security Basics

Most breaches in ordinary apps need no exploit: a key in a commit, a query built from a request field, a container running as root, a package with a published fix nobody installed. This skill runs the four checks in a fixed order with the scanner, the grep and the verdict for each, so a review ends in a table of findings rather than an opinion. The leading word is **exposure**: one secret, input path, privilege or package that someone outside the trust boundary can reach; each phase closes exposures of one kind.

Entry: the ask is a review, a hardening pass, or a finding from a scanner. A secret is already public or data is leaving now: Call the Skill tool with "incident-response" first (rotation is its mitigation), then return here for phase 1's purge. A version bump from phase 4 fails to install or drags a second requirer: Call the Skill tool with "dependency-troubleshooting". A secret printed by a log line, not stored in code: Call the Skill tool with "log-instrumentation" (its phase 3 redaction config). A `401` or `403` whose cause is unknown is an error, not a review: Call the Skill tool with "error-triage". An LLM prompt that must survive adversarial input (prompt injection): Call the Skill tool with "structured-prompting"; this skill owns injection into SQL, shells, paths and HTML only.

## 1. Secrets: tree, history, ignore rules

Run the scanner on the working tree and the full history (`detect --source .` on gitleaks below 8.19), then list what git tracks that it never should:

```sh
gitleaks git --redact -v . && gitleaks dir --redact .        # exit 1 and `leaks found: <n>` on a hit; `no leaks found` is the pass
trufflehog git file://. --only-verified --fail               # exit 183 only for a secret that still authenticates
git ls-files | grep -E '(^|/)\.env(\.|$)|\.(pem|p12|jks|key)$|id_(rsa|ed25519)$|credentials\.json$'
git check-ignore -v .env .env.local '*.pem'                  # prints the matching rule per path; silence means unignored
```

Rotate before you purge: a secret that was ever pushed is burned even after the rewrite (forks, CI caches, clones). Then purge with `git filter-repo --replace-text replacements.txt` (one `<literal>==>REDACTED` line per secret, run in a fresh clone; `Refusing to destructively overwrite repo history since this does not look like a fresh clone` means it was not, use `--force` only there), `git push --force --all && git push --force --tags`, and tell every clone owner to re-clone. Move each secret to the environment (`process.env.X`, `os.environ["X"]`, `${X}` in `application.yml`, `--dart-define`) with `.env*` in `.gitignore` and a committed `.env.example` holding names only.

**Done when** both gitleaks commands print `no leaks found`, the `git ls-files` grep returns 0 lines, `git check-ignore` prints a rule for every env and key path, and every secret the scan found has a line `rotated <where> <date>` in the report.

## 2. Input validation and injection at the boundary

Every handler parses its input against a schema before the first use; a front-end check is a convenience, never the control. Pin the stack's validator, then grep for the sinks:

| Stack | Validator at the boundary | Silent-failure tell |
| --- | --- | --- |
| Node / Express | `z.object({...}).safeParse(req.body)`; `express.json({ limit: '100kb' })` (the default; raise it deliberately) | a route reading `req.body.<field>` with no `safeParse` or `parse` above it |
| Django / DRF | `forms.Form` or a `Serializer` with `is_valid(raise_exception=True)`; `python manage.py check --deploy --fail-level WARNING` (python-django §1 lists the `security.W0xx` codes) | `request.POST['x']` or `request.GET.get('x')` used in a query or a path |
| Spring Boot | `@Valid @RequestBody` with `@NotBlank`, `@Size`, `@Pattern`; the `spring-boot-starter-validation` dependency | `@Valid` present but the starter missing: no `MethodArgumentNotValidException` ever, bad input accepted |
| Flutter / RN / Angular / React | client checks only; the server row above owns the control | a form validator with no matching server-side rule |

Sinks, one grep each; every hit is a finding unless the value is a constant or a parameterized placeholder:

| Exposure | Grep (adjust `src/` to the code root) | Replace with |
| --- | --- | --- |
| SQL built by string | `grep -rnE '(execute\|raw\|extra\|createNativeQuery\|createQuery\|query)\(.*(f"\|\+\|\$\{\|%s" %\|\.format\()' src/` | placeholders: `cursor.execute(sql, [x])`, `?` with `setParameter`, `$1` with a values array, the ORM filter |
| Shell from input | `grep -rnE 'shell=True\|child_process\.exec(\|\s)\|Runtime\.getRuntime\(\)\.exec\|os\.system\(' src/` | `execFile`/`spawn` with an args array, `subprocess.run([...])`, `ProcessBuilder(List)` |
| Path from input | `grep -rnE 'path\.join\(.*req\.\|os\.path\.join\(.*request\.\|Paths\.get\(.*request' src/` | resolve, then require `resolved.startsWith(base + sep)`; else 400 |
| HTML from input | `grep -rnE 'dangerouslySetInnerHTML\|bypassSecurityTrust\|mark_safe\|\|safe\b\|\.innerHTML\s*=' src/` | the framework's escaped binding; sanitize with DOMPurify or `bleach.clean` only for stored rich text |
| Deserialization | `grep -rnE 'pickle\.loads\|yaml\.load\(\|ObjectInputStream\|eval\(' src/` (a `yaml.load` hit passes only with `Loader=SafeLoader`) | `json.loads`, `yaml.safe_load`, a typed DTO; never a serialized object from a client |
| Mass assignment | `grep -rnE 'Model\(\*\*request\|fields = "__all__"\|\.\.\.req\.body\|Object\.assign\(.*req\.body' src/` | an explicit allow-list of fields in the schema or serializer |

Then one SAST pass that reads the code rather than its text: `semgrep scan --config p/owasp-top-ten --config p/secrets --error --metrics=off .` (exit 1 on a finding) and, for Python, `bandit -r src/ -ll -ii` (`>> Issue: [B608:hardcoded_sql_expressions]` is the SQL row above).

**Done when** every grep returns 0 lines or a per-hit finding row, semgrep and bandit exit 0 or their remaining findings are rows, and every handler in the service names the schema it parses.

## 3. Least privilege: who can do what

| Surface | Check | Pass |
| --- | --- | --- |
| Container | `docker run --rm --entrypoint id <image> -u`; `grep -n '^USER' Dockerfile` | prints a non-zero uid; a `USER` line after the install steps |
| Kubernetes | `kubectl get deploy <name> -o jsonpath='{.spec.template.spec.securityContext}{" "}{.spec.template.spec.containers[*].securityContext}'` | `runAsNonRoot:true`, `allowPrivilegeEscalation:false`, `readOnlyRootFilesystem:true` |
| Database user | `SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;` then `SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE grantee = current_user;` | all three flags `f`; no `DROP`, `TRUNCATE` or `REFERENCES`; migrations run as a separate role |
| Cloud IAM | `grep -rnE '"(Action\|Resource)":\s*"\*"' infra/ terraform/ .github/` | 0 lines; each statement names the actions and the ARN |
| CI token | top of each `.github/workflows/*.yml`: `permissions:` block | `contents: read` at the top, write scopes per job; no `pull_request_target` that checks out `github.event.pull_request.head.sha` |
| CORS | `grep -rnE 'allowedOrigins\("\*"\)\|origin:\s*(true\|"\*")\|CORS_ALLOW_ALL_ORIGINS\s*=\s*True\|Access-Control-Allow-Origin.*\*' src/` | an explicit origin list; Spring refuses the pair itself: `When allowCredentials is true, allowedOrigins cannot contain the special value "*"` |
| Framework switches | Django `DEBUG`, `ALLOWED_HOSTS`; Spring `management.endpoints.web.exposure.include`; Express `app.use(helmet())` | `DEBUG = False` and a host list in prod; actuator exposes `health,info` only (`env`, `heapdump` never public); helmet present once |

A privilege kept "for later" is an exposure now: drop it and note the ticket that would reinstate it.

**Done when** every row has a verdict line (`<surface>: pass` or a finding), and each finding names the one line or statement that narrows it.

## 4. Dependency audit at a threshold

Run the manager's own audit with a severity threshold so the exit code is the verdict, then the cross-stack scanner once:

| Manager | Command | Tell of a finding |
| --- | --- | --- |
| npm / pnpm / yarn | `npm audit --audit-level=high` (pnpm: `pnpm audit --audit-level high`; yarn: `yarn npm audit --severity high`) | exit 1; `<n> vulnerabilities (<a> moderate, <b> high)`; `found 0 vulnerabilities` is the pass |
| pip | `pip-audit -r requirements.txt --strict` or `pip-audit` inside the venv; preview fixes with `pip-audit --fix --dry-run` | exit 1; `Found <n> known vulnerabilities in <m> packages`; `No known vulnerabilities found` is the pass |
| Maven | `mvn org.owasp:dependency-check-maven:check -DfailBuildOnCVSS=7 -DnvdApiKey="$NVD_API_KEY"` | `One or more dependencies were identified with known vulnerabilities`; without the key the NVD download takes an hour or fails with `NVD Returned Status Code: 403` |
| Gradle | `./gradlew dependencyCheckAnalyze` with `failBuildOnCVSS = 7` in the plugin block | same report; `build/reports/dependency-check-report.html` |
| pub | `osv-scanner scan source -L pubspec.lock` (`dart pub outdated` shows what a bump would move) | exit 1 and a table with `OSV URL`, `CVSS`, `PACKAGE` columns |
| Any tree | `trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 1 .` | `Total: <n> (HIGH: <a>, CRITICAL: <b>)`; `Total: 0` is the pass |

Fix by bumping to the first fixed version named in the advisory, one package per commit, and rerun the audit; `npm audit fix --force` is a major bump of whatever it touches (`npm warn audit Updating <pkg> to <v>, which is a SemVer major change`) and is never the first move. A finding with no fixed version gets an ignore entry with the advisory ID, the reason and a 30-day expiry (`pip-audit --ignore-vuln <ID>`, `.trivyignore`, `dependency-check-suppressions.xml`, an `audit` block in `package.json` is not supported: use `overrides` to the fixed version instead). A package whose fix never lands: Call the Skill tool with "bug-report-writing" to file upstream with the advisory as the repro.

**Done when** every audit command exits 0 at the threshold, or every remaining finding has an ignore entry with ID, reason and expiry date, and the lockfile diff touches only the bumped packages.

## Report

```
Security review: <repo or service> at <sha>, <date>
| # | Exposure | Where | Severity | Fix | Verified by |
| --- | --- | --- | --- | --- | --- |
| 1 | <secret / injection / privilege / package> | <path:line or surface> | critical · high · medium · low | <one line, the command or diff> | <command and its pass line> |
Rotated: <secret> <where> <date> | none
Ignored: <advisory ID> <reason> <expiry> | none
Not checked: <surface> <why>
```

Severity: critical is reachable unauthenticated or already public; high needs an account; medium needs a second bug; low is hygiene. The stack skill owns the idiom of a fix (a Spring row: Call the Skill tool with "java-spring-stack"; a Node row: Call the Skill tool with "nodejs"; a Django row: Call the Skill tool with "python-django"); this skill owns the finding and its proof.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| Purging history before rotating | rotate, then `filter-repo`; the old value is burned either way |
| "Validated on the client" | the schema in the handler; the client check stays as UX |
| `npm audit fix --force` as step one | one advisory, one bump, one audit rerun |
| An ignore entry without expiry | ID, reason, date; expired entries are findings again |
| A review that ends in advice | the report table with a `Verified by` column |

## Example

**Ask:** "Can you do a quick security pass on the orders service before we open it to partners? Node 22, Express, Postgres, deployed on k8s."

1. `gitleaks git --redact -v .` exits 1: `leaks found: 1`, `RuleID: stripe-access-token`, `File: config/dev.env`, commit `a91c2e0`. `git ls-files | grep -E '\.env'` prints `config/dev.env`. Rotated in the Stripe dashboard (`rotated stripe 2026-10-16`), key moved to `STRIPE_KEY` env, `.env*` ignored, `.env.example` added, `git filter-repo --replace-text replacements.txt` in a fresh clone, force-pushed, team told to re-clone. Rerun prints `no leaks found`.
2. SQL grep hits `src/orders/repo.ts:41`: `` db.query(`SELECT * FROM orders WHERE status = '${status}'`) ``; replaced with `db.query('SELECT * FROM orders WHERE status = $1', [status])`. Path grep 0, shell grep 0, HTML grep 0. `safeParse` missing on `POST /orders`: `OrderSchema` added. semgrep exits 0 after the fix.
3. Container: `id -u` prints `0`; `USER node` added after `npm ci`. Deploy: securityContext empty; `runAsNonRoot: true`, `allowPrivilegeEscalation: false` added. DB: `rolsuper f`, grants show `DELETE` on `audit_log`; revoked. CI: no `permissions:` block; `contents: read` added. CORS: `origin: true`; replaced with the partner origin list.
4. `npm audit --audit-level=high`: `2 vulnerabilities (1 moderate, 1 high)`; `jsonwebtoken` bumped to 9.0.2 per GHSA-8cf7-32gw-wr33, rerun prints `found 0 vulnerabilities`; `trivy fs` prints `Total: 0`.

Report: 6 rows (1 critical: the key; 2 high: SQL, root container; 3 medium), `Rotated: stripe`, `Ignored: none`, `Not checked: IAM (no infra/ in this repo)`.
