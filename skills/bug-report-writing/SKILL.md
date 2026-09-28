---
name: bug-report-writing
description: Write a bug report that someone else will act on — a GitHub/GitLab issue against a library or upstream project, a ticket for another team, or a vendor support case. Use when the user asks to "file", "report", "open an issue for", or "write up" a bug, or to hand a defect to people who cannot see this conversation. Do not use when the goal is to diagnose or fix the bug here — error-triage owns an unclassified error and debug-from-raw-logs owns the investigation; come here once the smallest failing case exists and the deliverable is the write-up.
---

# Bug Report Writing

A bug report is a reproduction handed to a stranger. Maintainers close what they cannot run: reports without a version, without an exact command, or with a screenshot where text belongs. Assemble the seven fields below with the commands given, minimize the repro to the thresholds, then fill the template. Never file from a description alone.

## 1. Check it is not already filed (1 minute)

- Search open *and* closed issues with the literal error text, not the paraphrase:
  `gh issue list --repo <owner>/<repo> --state all --search "<exact error message>" --limit 20`
  (GitLab: `glab issue list --repo <group>/<project> --all --search "<text>"`).
- A hit that matches the version and stack trace ⇒ do not file; add a comment with the extra environment and repro (`gh issue comment <n> --body-file report.md`) and tell the user the issue number.
- Also check the changelog / release notes for the next version: `gh release view --repo <owner>/<repo>` — a fixed-in-unreleased bug needs a comment, not a new issue.

## 2. Collect the seven fields (reject the report if any is missing)

| # | Field | How to get it | Reject if |
| --- | --- | --- | --- |
| 1 | Exact version of the failing component | `npm ls <pkg> --depth=0` · `pip show <pkg> \| grep -i ^version` · `<tool> --version` · for a source checkout `git describe --tags --always --dirty` | "latest", "recent", or a range |
| 2 | Environment | JS: `npx envinfo --system --binaries --npmPackages <pkg> --markdown` · Python: `python -c "import sys,platform;print(sys.version);print(platform.platform())"` · always `uname -srm` (or `ver` on Windows) | OS or runtime version absent |
| 3 | Minimal repro | one file or one command, ≤ 30 lines, no private packages, no credentials, no network unless the bug is the network | needs the user's repo, DB, or account to run |
| 4 | Steps | numbered, each one a literal command or click; the last step is the one that fails | prose ("then I ran the tests") |
| 5 | Expected vs actual | *actual* is the verbatim first error line + exit code; *expected* cites the doc, type signature, or previous version that promised it | "it should work" |
| 6 | Logs / trace | the full trace, unedited, in a fenced block; for > 60 lines attach a file or a gist (`gh gist create run.log`) and inline only the first error | screenshot of text; trace trimmed to one line |
| 7 | Regression status | `<pkg>@<last good>` works? Say which version; if unknown, install the previous minor and re-run: `npm i <pkg>@<x.y-1>` / `pip install "<pkg>==<x.y-1>"` | omitted when the bug is new since an upgrade |

Redact before pasting any log: `sed -E 's/((Bearer|token=|api[_-]?key=|password=)[ ]?)[A-Za-z0-9._~+\/=-]{8,}/\1<REDACTED>/gI' run.log > run.redacted.log`, then `grep -inE 'bearer|token|secret|passw' run.redacted.log` must return nothing.

## 3. Minimize the repro to the thresholds

Work down from the user's failing case; stop when every threshold holds. If no failing case exists yet, run `debug-from-raw-logs` §3–4 first and come back with its repro command.

1. Remove one dependency, file, or input at a time; re-run after each removal. Keep a removal only if the failure still reproduces with the **same first error line**. A different error means you found a second bug — note it, revert the removal.
2. Replace real data with the smallest literal that still fails (an empty string, a one-row CSV, a 1-byte file with the offending byte: `printf '\xe9' > latin1.txt`).
3. Pin everything a maintainer cannot see: `package.json` with exact versions (no `^`), a lockfile, or a `requirements.txt` from `pip freeze | grep -i <pkg>`.
4. Measure the rate: `for i in $(seq 10); do <repro cmd> >/dev/null 2>&1 || echo FAIL; done | grep -c FAIL`. Report it as `n/10`; a 10/10 report gets fixed, a "sometimes" report gets a "cannot reproduce".
5. Thresholds: ≤ 30 lines, ≤ 1 file, ≤ 2 third-party packages besides the failing one, runs from a fresh clone/venv in ≤ 60 s. Above any of these, keep cutting or say in the report which threshold you could not meet and why.

## 4. Title formula and body template

Title, ≤ 80 characters: `<component>: <observed wrong behaviour> when <condition> (v<X.Y.Z>, since v<A.B>)`.
Good: `csv-reader: UnicodeDecodeError on Latin-1 input when encoding is unset (v3.2.0, since v3.2)`. Bad: `CSV import broken`, `Bug in reader`, `Doesn't work on Windows`.

```markdown
### Version / environment
<field 1 line, then field 2 output>

### Minimal reproduction
<field 3: fenced code or the command; say how to run it>

### Steps
1. …  2. …  3. <the step that fails>

### Expected
<field 5, with the doc/type/prior-version reference>

### Actual
<verbatim first error line, exit code, rate n/10>

<details><summary>Full trace</summary> <field 6> </details>

### Regression
<field 7: last known good version, or "unknown — first use">

### Notes
<one line: workaround if any; a suspected cause only if you tested it, phrased as a test result not a diagnosis>
```

File it: `gh issue create --repo <owner>/<repo> --title "<title>" --body-file report.md --label bug`. If the repo has an issue template (`gh api repos/<owner>/<repo>/contents/.github/ISSUE_TEMPLATE`), map the fields into its headings instead of using the template above.

## 5. Failure modes and their tells

| Failure mode | Observable tell | Fix |
| --- | --- | --- |
| Works-on-my-machine report | field 2 empty or "macOS"; maintainer's first reply asks for a version | run the field-2 commands, paste verbatim |
| Narrative report | steps are a paragraph; the failing step is not the last line | rewrite as numbered literal commands |
| Fix disguised as report | body proposes a patch and no repro; title names the cause ("mutex not released") not the symptom | move the theory to *Notes*, phrase as a tested result; title = symptom |
| Kitchen-sink repro | repro needs the user's monorepo, `.env`, or DB dump | §3 until ≤ 1 file / ≤ 30 lines |
| Leaked secret | `grep -inE 'bearer\|token\|secret\|passw'` on the body returns a hit | redact with the §2 `sed`; if already posted, rotate the secret first, then edit |
| Duplicate | `gh issue list --search` shows the same first error line | comment on the existing issue instead |

## Example

User: "Our CSV import crashes on some customer files since we upgraded `fastcsv`. Open an issue upstream."

1. `gh issue list --repo acme/fastcsv --state all --search "UnicodeDecodeError" --limit 20` → 0 matches. `gh release view --repo acme/fastcsv` → 3.2.0 is latest.
2. Fields: `pip show fastcsv` → 3.2.0; Python 3.12.4, `Linux 6.8 x86_64`. `pip install "fastcsv==3.1.2"` → import succeeds ⇒ regression since 3.2.
3. Minimize: `printf 'name\nJos\xe9\n' > latin1.csv`; repro `python -c "import fastcsv; fastcsv.read('latin1.csv')"` → `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9`, exit 1, 10/10. One file, 1 line, 1 package.
4. Title: `read(): UnicodeDecodeError on Latin-1 file when encoding is unset (v3.2.0, since v3.2)`. Expected cites the 3.1 docstring: "encoding defaults to the file's BOM, else latin-1". Notes: "Workaround: `read(path, encoding='latin-1')`."
5. `gh issue create --repo acme/fastcsv --title "…" --body-file report.md --label bug` → `#412`. Report the link and the workaround to the user.
