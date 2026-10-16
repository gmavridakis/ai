---
name: dependency-troubleshooting
description: Fix a dependency problem in any stack: an install that passes on one machine and fails on another, a lockfile in merge conflict or drifting between machines, two versions of one package in the tree, or a runtime tell naming a version mismatch (`NoSuchMethodError`, `cannot import name`, `NODE_MODULE_VERSION`). Do not use for a tell with its own stack row (ERESOLVE: nodejs; `version solving failed`: flutter-dart) or an unclassified error (error-triage).
---

# Dependency Troubleshooting

Dependency bugs are fixed by deleting `node_modules` and hoping far more often than by reading the resolver. The fix that lands is then `--force`, `--legacy-peer-deps` or a hand-edited lockfile, and the same failure returns on the next machine. This skill reads the resolved graph before any install, pins one version by the manager's own override mechanism, and proves it on a frozen install. The leading word is **tree**: the resolved graph as the manager prints it, with every requirer and the version that won.

Entry condition: the symptom is about which version of what is installed. A tell with its own row goes to the stack first and returns here only when that row's one-line fix leaves a second requirer: `ERESOLVE` or `npm ci` "not in sync": Call the Skill tool with "nodejs"; `version solving failed`: Call the Skill tool with "flutter-dart"; `javax.persistence does not exist`: Call the Skill tool with "java-spring-stack"; `Invalid hook call` with two `react` copies: Call the Skill tool with "react". An error whose layer is unknown (timeout, 4xx, "it fails"): Call the Skill tool with "error-triage" first. The ask is which packages carry a published vulnerability (`npm audit`, `pip-audit`, a `CVE-` or `GHSA-` ID) rather than which version is installed: Call the Skill tool with "security-basics"; it returns here when the fixed version will not install. A bug that survives a clean tree is code: Call the Skill tool with the stack skill the project pins.

## 1. Pin the manager, the lockfile, the runtime, and where it fails

Run the row for the project and write the four answers down before any install. "Works on my machine" is a difference in one of these rows until proven otherwise.

| Manager (files) | Lockfile | Frozen install (CI) | Runtime and manager version to compare |
| --- | --- | --- | --- |
| npm (`package-lock.json`) | commit it; `npm ci` | `npm ci` | `node -v` vs `.nvmrc` / `engines.node`; `npm -v` vs `packageManager` (`corepack enable`) |
| pnpm (`pnpm-lock.yaml`) | commit it | `pnpm install --frozen-lockfile` | same; tell `ERR_PNPM_OUTDATED_LOCKFILE  Cannot install with "frozen-lockfile" because pnpm-lock.yaml is not up to date with package.json` |
| yarn (`yarn.lock`, `.yarnrc.yml`) | commit it | `yarn install --immutable` (classic: `--frozen-lockfile`) | tell `YN0028: The lockfile would have been modified by this install, which is explicitly forbidden` |
| pip (`requirements.txt`, `pyproject.toml`) | `pip-compile` output or `uv.lock` | `uv sync --locked`; `pip install -r requirements.txt -c constraints.txt` | `python --version` vs `requires-python`; `pip --version` prints which interpreter it serves; tell `The lockfile at uv.lock needs to be updated, but --locked was provided` |
| Maven (`pom.xml`) | none: versions pinned in `dependencyManagement` | `./mvnw -B -U verify` | `java -version` vs `maven.compiler.release`; `./mvnw -v`, never a system `mvn` |
| Gradle (`build.gradle(.kts)`) | `gradle.lockfile` only with `dependencyLocking` | `./gradlew build --refresh-dependencies` once, then plain | `./gradlew -v` (wrapper); `java -version` vs toolchain |
| pub (`pubspec.yaml`) | `pubspec.lock` (commit for apps, not packages) | `flutter pub get --enforce-lockfile` | `flutter --version` vs `environment.sdk` |

Rows that differ between the passing and the failing machine, in order of frequency: runtime major, manager major, lockfile not committed (`git ls-files <lockfile>` prints nothing) or ignored, install flag not frozen in CI (`npm install` where `npm ci` belongs), OS or CPU (`node -p process.platform+'-'+process.arch`, `python -c "import sysconfig;print(sysconfig.get_platform())"`: a lockfile written on `darwin-arm64` and installed on `linux-x64`), a stale cache (the failing machine passes after the phase 4 clean install with nothing else changed). Fix the differing row and re-run before reading any code.

**Done when** manager, lockfile path, runtime version on both machines, and the install command that fails are four lines in the reply, and every row that differs between machines is named.

## 2. Read the tree: every requirer, the winner, the loser

| Manager | Who requires it | The tree's conflict marker |
| --- | --- | --- |
| npm | `npm explain <pkg>` (alias `npm why`); `npm ls <pkg> --all` | `deduped` (shared copy), `invalid: "^2.0.0" from node_modules/<x>` (constraint not met), two version lines (two copies) |
| pnpm | `pnpm why <pkg>` | each path printed once per version |
| yarn | `yarn why <pkg>` | `Reasons this module exists` list |
| Maven | `./mvnw dependency:tree -Dverbose -Dincludes=<group>:<artifact>` | `omitted for conflict with <v>` (nearest wins), `version managed from <v>` (dependencyManagement wins) |
| Gradle | `./gradlew dependencyInsight --dependency <artifact> --configuration runtimeClasspath` | `By conflict resolution: between versions <a> and <b>` (highest wins), `Selected by rule`, `(c)` constraint |
| pip / uv | `pip check` (prints `<pkg> <v> has requirement <req>, but you have <pkg> <v>`); `pipdeptree -r -p <pkg>`; `uv tree --invert --package <pkg>` | `ResolutionImpossible` with the `The conflict is caused by:` block |
| pub | `dart pub deps -s compact`; `flutter pub outdated` | `Because <a> depends on <p> ^X and <b> depends on <p> ^Y` |

Locate the copy the runtime actually loads, not the one the manifest names: Node `node -p "require.resolve('<pkg>/package.json')"` then `node -p "require('<pkg>/package.json').version"`; Python `python -c "import <pkg>,sys;print(<pkg>.__file__,sys.executable)"` (a path outside the project's `.venv` is the bug); JVM `./mvnw dependency:build-classpath -Dmdep.outputFile=cp.txt` then `for j in $(tr ':' ' ' < cp.txt); do unzip -l "$j" | grep -q '<Class>.class' && echo "$j"; done` (two jars printed is the bug). Resolution rule by manager: Maven takes the nearest declaration, Gradle the highest version, npm nests a second copy, pip and pub refuse.

**Done when** the reply lists every requirer of the conflicting package with its constraint, the version that won and why (nearest, highest, nested, managed), and the path of the copy the runtime loads.

## 3. Resolve with one change in the manifest

Pick the first matching row. One change, then the frozen install of phase 1 must exit 0.

| Tree shape | Change |
| --- | --- |
| One requirer is the outlier (an old plugin wanting `^2` while everything else is on 3) | bump that requirer; if it has no release that accepts the version, replace it or open its issue |
| A library's constraint is too tight but the newer version works | override (table below); add `# <issue url>` next to it and a date; remove at the next bump |
| Two copies at runtime (two jars, two `react`, two `node_modules/<pkg>`) | Maven: `<exclusions>` on the dependency that drags the old one, or `dependencyManagement`; Gradle: `constraints`; npm: `npm dedupe` then `overrides` |
| Lockfile out of sync with the manifest | regenerate locally with the manager (`npm install --package-lock-only`, `pnpm install`, `yarn install`, `uv lock`, `flutter pub get`), commit the lockfile, keep CI frozen |
| Lockfile with `<<<<<<<` markers after a merge | never edit by hand: `git checkout --theirs <lockfile>` (or `--ours`), then the manager's plain install regenerates it from the merged manifest; commit |
| Native module: `was compiled against a different Node.js version using NODE_MODULE_VERSION <n>. This version of Node.js requires NODE_MODULE_VERSION <m>` | `node -v` differs from the install's; `npm rebuild <pkg>` after switching, or pin Node in `engines` and `.nvmrc` |
| `pip check` conflict with no manifest change | the environment was reused across branches: phase 4's clean install, then the row above that matches |
| `Error: Cannot find module '@rollup/rollup-linux-x64-gnu'` (also `@esbuild/linux-x64`, `@swc/core-linux-x64-gnu`, `Could not load the "sharp" module using the linux-x64 runtime`) only on the other OS | npm wrote the lockfile without that platform's optional dependency (npm/cli issue 4828): on any machine `npm install --os=linux --cpu=x64` (npm 10.4+) adds the entry, commit the lockfile, `npm ci` on the failing machine; `rm -rf node_modules package-lock.json && npm install` is the fallback for older npm |

Override syntax (Oct 2026):

| Manager | Where | Literal |
| --- | --- | --- |
| npm 8.3+ | `package.json` | `"overrides": { "<pkg>": "<version>" }`; nested: `"<parent>": { "<pkg>": "<version>" }` |
| pnpm | `package.json` | `"pnpm": { "overrides": { "<pkg>": "<version>" } }` |
| yarn | `package.json` | `"resolutions": { "<pkg>": "<version>" }` |
| Maven | `pom.xml` | `<dependencyManagement><dependencies><dependency>` with the version; per-path `<exclusions><exclusion>` |
| Gradle | `build.gradle.kts` | `dependencies { constraints { implementation("<g>:<a>:<v>") { because("<reason>") } } }`; last resort `configurations.all { resolutionStrategy.force("<g>:<a>:<v>") }` |
| pip | `constraints.txt` passed with `-c` | `<pkg>==<version>` |
| uv | `pyproject.toml` | `[tool.uv] override-dependencies = ["<pkg>==<version>"]` |
| pub | `pubspec.yaml` | `dependency_overrides:` then `  <pkg>: <version>` (pub get prints `Warning: You are using these overridden dependencies`) |

**Done when** exactly one manifest file changed, the frozen install command of phase 1 exits 0, and `git diff --stat` of the lockfile shows only the intended package and its direct dependents.

## 4. Prove it on a clean install, then on the other machine

Clean means the manager's cache and the install directory, not the lockfile.

| Manager | Clean install |
| --- | --- |
| npm | `rm -rf node_modules && npm cache verify && npm ci` |
| pnpm | `rm -rf node_modules && pnpm store prune && pnpm install --frozen-lockfile` |
| yarn | `rm -rf node_modules && yarn cache clean && yarn install --immutable` |
| pip / uv | `python -m venv .venv --clear && .venv/bin/pip install --no-cache-dir -r requirements.txt -c constraints.txt`; uv: `rm -rf .venv && uv sync --locked` |
| Maven | `rm -rf ~/.m2/repository/<group path> && ./mvnw -B -U clean verify` |
| Gradle | `rm -rf ~/.gradle/caches/modules-2/files-2.1/<group> && ./gradlew clean build --refresh-dependencies` |
| pub | `flutter clean && dart pub cache repair && flutter pub get --enforce-lockfile` |

After it: `git status --short <lockfile>` prints nothing (the install did not rewrite the lock), the phase 2 locate command prints one path, and the original tell is gone from one run of the failing command. Then the same install on the machine that failed, or in CI, with the runtime pinned in phase 1.

**Done when** the clean install exits 0 with an unchanged lockfile, the locate command prints one path, the original command runs without the tell, and the CI or second-machine run id is in the reply.

## Runtime tells that are dependency problems

| Tell | Meaning | Phase 2 command |
| --- | --- | --- |
| `java.lang.NoSuchMethodError: '<signature>'` or `NoClassDefFoundError` for a class that is in the jar | two versions on the classpath; the older one loaded first | the `unzip -l` loop over `cp.txt` |
| `ImportError: cannot import name '<x>' from '<pkg>'` / `AttributeError: module '<pkg>' has no attribute '<x>'` | an older copy outside the venv shadows the installed one, or a local file named like the package | `python -c "import <pkg>;print(<pkg>.__file__)"` |
| `Error: Cannot find module '<pkg>'` only in production | the package sits in `devDependencies` and the image ran `npm ci --omit=dev` | `npm explain <pkg>` shows `dev` |
| Two `Reasons this module exists` entries at different versions | nested copies; a singleton (react, a logger, a DI container) breaks | `npm ls <pkg> --all` |
| `ERROR: No matching distribution found for <pkg>==<v>` on one machine only | the pinned release ships no wheel or sdist for that machine's Python or platform tags | `pip index versions <pkg>` lists what resolves there; `pip debug --verbose \| grep -c cp3` shows the tags; the phase 1 runtime or OS row differs |

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| `--force`, `--legacy-peer-deps` or `--no-deps` in a committed script or `.npmrc` | phase 3 row with an override and its issue link |
| Lockfile deleted "to fix it", or edited by hand | regenerate from the manifest; `--theirs` on a merge |
| `npm install` in CI, `pip install` without a constraints file | the frozen column of phase 1 |
| `mavenLocal()` or a system `mvn` / `gradle` instead of the wrapper | the wrapper; the Done-when of phase 4 fails otherwise |
| Override left without a date or reason | `# <issue url> <date>` beside it; removed at the next bump |

## Example

**Ask:** "After adding the reporting library, the Spring Boot app starts locally but on the CI runner it dies with `java.lang.NoSuchMethodError: 'com.fasterxml.jackson.databind.ObjectMapper com.fasterxml.jackson.databind.ObjectMapper.findAndRegisterModules()'`."

1. Pin: Maven, no lockfile, `./mvnw -v` 3.9.9 on both; local `java -version` 21, CI runner 17 with `maven.compiler.release=17`; failing command `java -jar target/app.jar`. Local resolved from a warm `~/.m2`, CI from an empty one: the cache row differs.
2. Tree: `./mvnw dependency:tree -Dverbose -Dincludes=com.fasterxml.jackson.core:jackson-databind` prints `jackson-databind:2.17.2 (version managed from 2.9.8)` under `spring-boot-starter-json` and `jackson-databind:2.9.8 (omitted for conflict with 2.17.2)` under `com.acme:reporting-lib:4.1.0`; but `reporting-lib` also shades `com.fasterxml.jackson.databind` into its own jar. The `unzip -l` loop over `cp.txt` prints two jars for `ObjectMapper.class`: `jackson-databind-2.17.2.jar` and `reporting-lib-4.1.0.jar`. Two copies at runtime; the shaded 2.9.8 loads first on CI's classpath order.
3. Resolve: row "two copies"; `reporting-lib` 4.2.0 ships without the shaded Jackson, so bump the requirer: one line in `pom.xml`. `./mvnw -B -U verify` exits 0.
4. Prove: `rm -rf ~/.m2/repository/com/acme && ./mvnw -B -U clean verify`, the loop prints one jar, `java -jar target/app.jar` starts; CI run 8841 green. Reply carries the four pin lines, the two tree lines, the one-line change and the run id.
