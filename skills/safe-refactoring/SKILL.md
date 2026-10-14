---
name: safe-refactoring
description: Change code structure while behaviour stays identical: rename, extract, inline, move, split a file, delete dead code, migrate call sites, or anything the user calls "refactor", "clean up", "simplify", "reorganise", "break up", "modernise". Use for the step size, the proof that nothing changed, and the commit discipline. Do not use to change what the code does or how fast (the stack skill, performance-profiling) or once a step goes red (debug-from-raw-logs).
---

# Safe Refactoring

A refactor goes wrong in one of two ways: the change is too big to read, so a behaviour change rides along unseen, or the proof is "tests pass" with no record of what passed before. This skill cuts the work into steps, each proven by the same oracle before and after, read line by line for behaviour, and committed alone. The leading word is **step**: one named refactoring, applied once, green on both sides, in its own commit.

Entry condition: the target shape is agreed and the code works today. The idiom the code should end in (what a service, hook, view or widget looks like in this stack) comes from the stack skill: in a Spring project Call the Skill tool with "java-spring-stack"; in a Node service Call the Skill tool with "nodejs"; in a Django project Call the Skill tool with "python-django"; in an Angular workspace Call the Skill tool with "angular"; in a React or Next.js app Call the Skill tool with "react"; in a React Native or Expo app Call the Skill tool with "react-native"; in a Flutter app Call the Skill tool with "flutter-dart". A change whose goal is a different output, a new feature, or a faster path is not a refactor: the stack skill owns the first two, Call the Skill tool with "performance-profiling" for the third, and keep the structural part as its own steps before it. The user wants how long the refactor will take or whether it fits a sprint, not its steps: Call the Skill tool with "estimation-and-scoping" (it slices the work; this skill then runs each slice). A step that goes red and stays red after one revert-and-retry: Call the Skill tool with "debug-from-raw-logs" with the red command. A step that bumps a dependency major and the install fails: Call the Skill tool with "dependency-troubleshooting". "Clean up the logging", "too noisy", or any step whose only subject is which log lines exist and what they print: Call the Skill tool with "log-instrumentation"; a move or extract of logging code with identical output stays here. Before any step on more than 5 files: Call the Skill tool with "context-hygiene".

## 1. Fence: name the refactoring, fix the oracle, cover the touched lines

Write three lines before editing: the refactoring by catalog name (table below), the files it touches (`git grep -l '<symbol>'` count), and the **oracle**: the one command that must print the same result before and after. `git status --short` must be empty first; stash or commit anything else.

| Stack | Oracle (run once now, keep the counts) | Touched-line coverage |
| --- | --- | --- |
| Node / TS | `npx vitest run --reporter=dot` or `npx jest --ci --silent` (`Tests: <n> passed, <n> total`) | `npx vitest run --coverage --coverage.include='<file>' --coverage.reporter=text` |
| Python | `pytest -q -p no:cacheprovider` (`<n> passed in <s>s`) | `pytest --cov=<pkg> --cov-report=xml && diff-cover coverage.xml --compare-branch=main --fail-under=100` |
| JVM | `./mvnw -q -B test` (`Tests run: <n>, Failures: 0, Errors: 0, Skipped: <k>`) or `./gradlew test` | JaCoCo `target/site/jacoco/index.html` for the class, or `diff-cover` on `jacoco.xml` |
| Flutter | `flutter test --reporter=compact` (`+<n>: All tests passed!`) | `flutter test --coverage && lcov --list coverage/lcov.info` |
| Angular | `ng test --watch=false --browsers=ChromeHeadless` (`TOTAL: <n> SUCCESS`) | `ng test --watch=false --code-coverage` |

A touched function with no test that reaches it gets a **characterization test** first: call it with 5 to 20 recorded inputs, write the outputs to `<test dir>/golden/<fn>.json` once, assert equality from then on. Commit that test alone before step 1. Shape of the test (Python; the same three lines in any stack):

```python
CASES = json.load(open(GOLDEN))            # [{"in": {...}, "out": ...}, ...] recorded once from the current code
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_<fn>_golden(case): assert <fn>(**case["in"]) == case["out"]
```

**Done when** the three lines are in the reply, the oracle exits 0 with its pass count and skip count written down, and every function the refactoring touches is reached by at least one test (coverage row at 100% on touched lines, or the golden test committed).

## 2. Step: apply one refactoring, mechanically where a tool exists

One step is one catalog row, at most 200 changed lines (`git diff --stat | tail -1`), and never two rows at once (a rename inside an extract is two steps). Prefer the tool that rewrites the AST over hand edits: it cannot drop a call site.

| Refactoring | Tool (Oct 2026) | Check right after |
| --- | --- | --- |
| Rename symbol | IDE/LSP rename; TS without an LSP: `ast-grep run -p '$X.<old>($$$A)' -r '$X.<new>($$$A)' -l ts -U`; Python: `python -m libcst.tool codemod rename.RenameCommand --old_name <pkg>.<old> --new_name <pkg>.<new> <src>`; Java: `./mvnw -U org.openrewrite.maven:rewrite-maven-plugin:dryRun -Drewrite.activeRecipes=org.openrewrite.java.ChangeMethodName -Drewrite.recipeArtifactCoordinates=...` then `:run` | `git grep -n '\b<old>\b'` prints nothing (strings and docs included) |
| Extract function / class | hand edit from the IDE's Extract; keep parameter order equal to the first call site | `git diff --color-moved=dimmed-zebra`: the body is dim (moved), only the call and signature are bright |
| Inline | the reverse; delete the definition in the same step | `git grep -n '<fn>'` prints nothing |
| Move file / module | `git mv <old> <new>`, then the rename tool on imports | `git diff -M50% --stat` shows `<old> => <new>` with a similarity over 50% |
| Split a file | `git mv` to the larger half first, then extract the smaller into a new file | both halves listed by `git diff -M50% --stat`; no function appears twice (`git grep -c 'def <fn>'` is 1) |
| Delete dead code | `npx knip` (TS), `vulture <src> --min-confidence 80` (Python), `./mvnw dependency:analyze` plus IDE "unused", `dart analyze` `unused_element` | the oracle count is unchanged (a dropped test means the code was not dead) |
| Modernise syntax | `ruff check --select UP --fix --diff <src>` (`--diff` prints, drop it to write), `dart fix --dry-run` then `dart fix --apply`, OpenRewrite `org.openrewrite.java.migrate.UpgradeToJava21`, `npx jscodeshift -t <transform>.ts --parser tsx --dry --print <src>` then without `--dry` | compile gate below, then the oracle |
| Migrate call sites of a public API | **parallel change**: step A add the new API beside the old; step B move callers one package per step; step C delete the old. Never A and C together when `git grep -c '<old>'` exceeds 20 or another repo calls it | step C only when `git grep -n '<old>'` prints nothing |

Compile gate before the oracle: `npx tsc --noEmit -p .`; `mypy <pkg>` or `pyright`; `./mvnw -q compile`; `dart analyze`; `ng build --configuration=development`.

**Done when** the diff holds one catalog row, `git diff --stat` ends under 200 changed lines, the compile gate exits 0, the oracle exits 0 with the same pass and skip counts as phase 1, and `git diff --stat -- '*test*' '*spec*'` lists nothing but the golden test.

## 3. Read the diff for behaviour, not for style

Run the three commands and classify every bright line; a line you cannot classify is a behaviour change until proven otherwise.

| Command | What it isolates |
| --- | --- |
| `git diff -w --ignore-blank-lines --stat` against `git diff --stat` | files that differ only in whitespace: formatting rode along, move it to its own step |
| `git diff --color-moved=dimmed-zebra --color-moved-ws=allow-indentation-change` | moved blocks dim; a bright line inside one is an edit made during the move |
| `git diff -M50% --stat` | renames and splits as `=>`, not as a delete plus an add |

| Behaviour leak (bright line) | Tell | Fix |
| --- | --- | --- |
| Default argument or config value changed | a literal on a bright line (`= 30`, `"utf-8"`, `null`) | restore it; a value change is its own non-refactor commit |
| Conditions reordered around a side effect | `if` chain or `&&` operands swapped where one calls a function | keep the order; extract first, reorder later with a test |
| Exception type or message changed | `raise`/`throw` or a message string on a bright line | callers and alerts match on it; restore |
| Iteration order changed | `Set`, `dict`, `HashMap` replaced one another, or a `sort` dropped | output order is behaviour when it reaches a user or a file |
| Null path dropped | an `if (x == null)` or `?.` that disappeared | restore; the golden test did not cover it |
| Log line changed or removed | a logger call on a bright line | keep message and fields; a wanted change to them is its own commit: Call the Skill tool with "log-instrumentation" |

**Done when** every bright line is classified as signature, call-site, import, or move, no row of the leak table matches, and `git diff -w --ignore-blank-lines --stat` and `git diff --stat` list the same files.

## 4. Commit the step alone and prove the chain

One commit per step, with `git add -p` when anything else is in the tree. Message shape:

```
refactor(<scope>): <catalog row> <old> -> <new>

Behaviour unchanged: <oracle command> <n> passed, <k> skipped before and after.
```

Then the next step starts from phase 2. The reply's proof line ("behaviour unchanged" with the counts) is an evidence row in response-self-review: Call the Skill tool with "response-self-review" before sending. Before the branch is handed over: `git rebase -x '<oracle>' main` (non-interactive) runs the oracle on every commit; a red commit is bisectable to one step. A commit whose message needs "and" holds two steps: `git reset -p HEAD~1`, split, recommit.

**Done when** `git log --oneline main..HEAD` lists one line per step, each message carries the oracle count, `git rebase -x '<oracle>' main` exits 0, and `git status --short` is empty.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| "Refactored and fixed the bug" in one commit | the fix in its own commit with a red test first; the refactor steps around it |
| A test edited so it passes after the step | the test was the oracle; revert the step, read the bright line (phase 3) |
| Pass count dropped (412 to 409) with the suite "green" | tests skipped or deleted; `git diff --stat -- '*test*'` names them |
| A format-all run inside a rename | formatting as its own step, `git diff -w --stat` empty for the rename |
| `--force` rename by `sed` over strings | the AST tool row; `sed` renames inside strings, comments and other symbols sharing the prefix |
| 1,200-line diff "to be reviewed as one" | parallel change rows; a reviewer reads 200 lines per step |

## Example

**Ask:** "Break up `invoices/views.py` (640 lines); the `export_csv` view does validation, totals and the CSV in one function. Keep the output byte-identical, the finance team diffs these files."

1. Fence: refactoring = extract function (three: `validate_filters`, `compute_totals`, `write_rows`), files = 1 plus tests; oracle `pytest -q -p no:cacheprovider tests/invoices` prints `57 passed, 2 skipped`. `diff-cover` on touched lines: 61%, the totals branch for credit notes is unreached. Golden test: 12 recorded filter sets written to `tests/invoices/golden/export_csv.json` from the current view, `test_export_csv_golden` added and committed alone: `58 passed, 2 skipped`.
2. Step 1: extract `compute_totals` (IDE Extract, parameters in call-site order). `git diff --stat` ends `2 files changed, 41 insertions(+), 33 deletions(-)`. `mypy invoices` exits 0; oracle `58 passed, 2 skipped`.
3. Read: `--color-moved=dimmed-zebra` shows the body dim, two bright lines: the signature and the call. One more bright line: `round(total, 2)` became `round(total)`; leak row "default argument changed". Restored. `git diff -w --stat` and `git diff --stat` both list the same 2 files.
4. Commit `refactor(invoices): extract compute_totals from export_csv` with `Behaviour unchanged: pytest -q tests/invoices 58 passed, 2 skipped before and after.` Steps 2 and 3 repeat phases 2 to 4; `git rebase -x 'pytest -q tests/invoices' main` exits 0 on 4 commits; `git log --oneline main..HEAD` shows 4 lines, the golden test first.
