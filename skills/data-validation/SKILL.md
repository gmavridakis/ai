---
name: data-validation
description: Define and test what data must satisfy at a boundary: a per-field contract (nullable, range, length unit, unknown keys), an edge-case matrix (null, empty, unicode, NaN, leap days), property tests, one rejection shape. Use for "validate this input", "handle edge cases", a CSV or JSON import, `ValidationError`, "Invalid input: expected", an emoji or accent bug. Do not use for injection or a missing validator (security-basics) or an unknown cause (error-triage).
---

# Data Validation

Most data bugs are a rule nobody wrote down: a field that is "required" but arrives as `""`, a name limit counted in bytes by the database and in emoji by the user, a date that parses on one machine and not another. This skill writes the rules as a contract, turns the contract into a schema and a fixed matrix of edge cases, proves it with a property test, and fixes the rejection shape so a caller can act on it. The leading word is **guard**: one rule, enforced at one boundary, that turns a bad value into a rejection with a path and a code.

Entry: the ask is to validate, parse, import, or "handle edge cases" for data crossing a boundary (request body, file, message, config, spreadsheet). The value reaches SQL, a shell, a path or HTML, or the handler has no validator at all: Call the Skill tool with "security-basics" (its phase 2 owns injection and the missing validator; this skill owns what the validator says and how it is tested). The failing layer is unknown (a 500, a timeout): Call the Skill tool with "error-triage". A property test finds a counterexample whose cause is deeper than the schema: Call the Skill tool with "debug-from-raw-logs" with the shrunk example as the red. The idiom of the schema in a framework belongs to the stack skill (Call the Skill tool with "java-spring-stack", "python-django", "nodejs", "flutter-dart", "react", "react-native", or "angular").

## 1. Write the contract, then the schema

One row per field, before any code. Absent, `null` and `""` are three different values; the contract says which are accepted and what each means.

```
| Field | Type | Absent | null | Empty | Range or length (unit) | Format | On failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <name> | <type> | reject · default <v> | reject · means <x> | reject · means <x> | <min>..<max> <graphemes · bytes · items> | <regex · enum · ISO 8601> | <code> |
Unknown keys: reject · strip   Max body: <n> KB   Normalize: NFC, trim
```

Length unit: graphemes when the limit is shown to a user, bytes when it is a storage limit (`VARCHAR(n)` is characters in Postgres and MySQL utf8mb4, bytes in Oracle `BYTE` semantics), items for arrays. Then pin the schema in the stack's validator with unknown keys rejected and coercion off:

| Stack | Schema | Verbatim tell of a rejection |
| --- | --- | --- |
| Node (zod 4) | `z.object({ name: z.string().trim().min(1).max(80) }).strict()`; `schema.safeParse(body)`; print with `z.prettifyError(r.error)` (`z.formatError` is deprecated) | `✖ Invalid input: expected string, received number` then `→ at name`; `✖ Unrecognized key: "extraKey"` |
| Python (pydantic 2) | `model_config = ConfigDict(strict=True, extra='forbid')`; `Model.model_validate(data)` (`strict=True` per call for a lax model) | `Input should be a valid integer [type=int_type, input_value='123', input_type=str]`; `Field required [type=missing` ; `Extra inputs are not permitted [type=extra_forbidden` |
| Django / DRF | a `Serializer` with `is_valid(raise_exception=True)`; `extra_kwargs` for `max_length`, `allow_blank=False` (the default) | `{"name": ["This field may not be blank."]}`; `["This field is required."]` |
| Spring Boot | `@Valid @RequestBody Dto` with `@NotBlank @Size(max = 80) @Pattern`; `spring.jackson.deserialization.fail-on-unknown-properties=true` | `MethodArgumentNotValidException` for the body; `HandlerMethodValidationException` once a constraint sits directly on a parameter (`@Valid` alone does not trigger it) |
| Dart | `json_serializable` with `@JsonSerializable(checked: true, disallowUnrecognizedKeys: true)` | `CheckedFromJsonException: Unrecognized keys: [extra]`; `type 'Null' is not a subtype of type 'String'` means `checked` is off |
| Tabular file | `pandera`: `pa.DataFrameSchema({"qty": pa.Column(int, pa.Check.ge(0), nullable=False)}, strict=True)`; `schema.validate(df, lazy=True)` | `SchemaErrors` with a `failure_cases` frame: one row per bad cell, columns `column`, `check`, `failure_case`, `index` |

**Done when** every field in the payload has a contract row, the schema has a rule for each row, and a request with one unknown key is rejected with that key's name in the message.

## 2. The edge-case matrix

Apply every row to every field of that type; each cell becomes one test case with a verdict (`accept` with the stored value, or `reject <path> <code>`).

| Type | Cases (each one test) |
| --- | --- |
| Any | absent; `null`; wrong type (`"1"` for 1, `1` for `"1"`, `[]` for an object); the field twice (last wins in JSON: a rule, not an accident) |
| String | `""`; `" "`; 1 char; `max`; `max + 1`; leading/trailing space; NUL `\u0000`; a control char `\u001f`; `​` zero-width space; `‮` RTL override; `é` as NFC (1 code point) and NFD (`e` + `́`, 2); `👨‍👩‍👧` (1 grapheme, 5 code points, 8 UTF-16 units, 18 bytes); a lone surrogate `\ud83d`; `Ω` vs `Ω` (U+2126 vs U+03A9) |
| Number | `0`; `-0`; negative; `max`; `max + 1`; `2**53` (`Number.MAX_SAFE_INTEGER + 1`); `1e309` (parses to `Infinity`); `NaN`; `"1e3"` and `"007"` as strings; `0.1 + 0.2`; a float where an int is required (`1.0`, `1.5`) |
| Boolean | `"false"` (a non-empty string, truthy in JS and Python); `0`/`1`; `"yes"`; `null` |
| Date / time | `2024-02-29` (valid) and `2023-02-29` (not); `2024-13-01`; `24:00:00`; no offset (`2024-06-01T10:00:00` is local on one parser and UTC on another); `Z` vs `+00:00`; epoch seconds vs milliseconds (`1718000000` vs `1718000000000`); DST gap `2026-03-29T02:30` in Europe/Athens |
| Collection | `[]`; 1 item; `max`; `max + 1`; duplicates when unique; nesting past depth 3; `{}` for a list |
| Identifier | `0`; negative; nil UUID `00000000-0000-0000-0000-000000000000`; uppercase UUID; an id the caller may not see (authorization, not validation) |

**Done when** every (field, row) cell has a test with a verdict and the test file names the cell in its test name (`test_name_rejects_nfd_combining`).

## 3. Prove it with properties

Table cases pin what you thought of; a property test finds the rest. Three properties hold for any schema: round-trip (`parse(serialize(parse(x))) == parse(x)`), normalize is idempotent (`norm(norm(s)) == norm(s)`), and every rejection names a path.

| Stack | Generator for the worst strings | Tell of a find |
| --- | --- | --- |
| Python | `from hypothesis import given, strategies as st`; `@given(st.text())` (no surrogates by default); `st.text(alphabet=st.characters(codec="utf-8"), max_size=200)`; `st.from_type(Model)` builds whole payloads | `Falsifying example: test_x(s='\x00')` then the traceback; rerun it forever with `@example('\x00')` |
| Node | `fc.assert(fc.property(fc.string({ unit: 'grapheme' }), (s) => ...), { numRuns: 500 })`; `unit: 'binary'` adds control chars (`fc.fullUnicodeString` and `fc.unicodeString` are deprecated since 3.22) | `Property failed after <n> tests`, `Counterexample: [""]`, `Shrunk <k> time(s)`; pin with `fc.assert(..., { examples: [['']] })` |
| Java | jqwik: `@Property void name(@ForAll @StringLength(max = 80) String s)`; `@ForAll("unicode")` with a `@Provide` `Arbitraries.strings().all()` | `Shrunk Sample (<n> steps)` followed by the smallest failing value; pin with `@Example` |
| Any | the Big List of Naughty Strings as a fixture (`blns.json`, one case per entry) | a parser exception instead of a rejection: the schema has a gap, not the data |

**Done when** each property runs at least 200 examples per field with no falsifying example, and every counterexample found on the way is pinned as a named table case.

## 4. Normalize, then reject with a shape

Normalize before the schema sees the value, in this order: decode as UTF-8 (reject on failure, never replace), NFC (`unicodedata.normalize("NFC", s)`, `s.normalize("NFC")`, `Normalizer.normalize(s, Form.NFC)`), trim, then reject `[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]` and `‮`. Count graphemes with `Intl.Segmenter`, the `regex` module's `\X`, or `BreakIterator.getCharacterInstance()`; `len()` and `.length` count code points and UTF-16 units. One request with three bad fields returns all three, under one status (400 for a malformed body, 422 for a well-formed body that fails the contract; pick one per service and keep it), echoing a value only when it is under 100 characters:

```json
{ "status": 422, "errors": [ { "path": "<field.path[0]>", "code": "<too_long · missing · invalid_format · unknown_key>", "message": "<what was expected>", "received": "<value under 100 chars or omitted>" } ] }
```

**Done when** the three-bad-fields request returns three error entries each with `path` and `code`, and a NFD and an NFC spelling of the same name store the same bytes.

## Anti-patterns

| Tell | Replace with |
| --- | --- |
| `if (!value)` as the required check | explicit `=== undefined`, `=== null`, `=== ""` branches per the contract row (`0` and `false` are values) |
| `max_length=80` with no unit | the contract's unit and a grapheme or byte counter to match |
| Coercion on by default (`"1"` accepted as 1) | strict mode; coerce only on the fields the contract marks |
| First error only | `lazy=True`, `safeParse`, `e.errors()`: every error in one response |
| A regex for email or URL from memory | the library type (`z.email()`, `EmailStr`, `@Email`) plus a send or fetch in the integration test |

## Example

**Ask:** "Customers import from a CSV: name, email, birth date, credit limit. It crashes on some rows and lets others through that break the UI. Django, pandas, Postgres."

1. Contract: `name` string, absent and `""` reject, 1..80 graphemes, NFC; `email` lowercase, `EmailField`; `birth_date` `YYYY-MM-DD`, reject future; `credit_limit` int 0..1_000_000, absent means 0, `null` rejects; unknown columns reject. pandera schema with `strict=True`, `lazy=True`. A file with an extra column `notes` fails with `failure_case: notes`, `check: column_in_schema`.
2. Matrix: 34 cases; `2023-02-29` and `1e309` and `"👨‍👩‍👧" * 20` (20 graphemes, 160 UTF-16 units) each a named test; the emoji row revealed the UI counted 160 and truncated.
3. `@given(st.text(alphabet=st.characters(codec="utf-8"), max_size=200))` on `name`: `Falsifying example: test_name_roundtrip(s='é')` (NFD not equal after round trip). Pinned with `@example('é')`; 500 examples pass after phase 4's NFC step.
4. Normalize NFC, trim, strip control chars before `schema.validate`; the import endpoint returns 422 with one entry per bad cell (`path: "row[17].birth_date"`, `code: "invalid_format"`); 3 bad rows in the sample file give 3 entries.
