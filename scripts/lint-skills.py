#!/usr/bin/env python3
"""Lint skills/*/SKILL.md against docs/conventions.md.

Usage: python3 scripts/lint-skills.py [skills/<name>/SKILL.md ...]
Exit 1 on any error. Warnings are printed but do not fail the run.

Errors:   name matches folder; description <= 70 words (<= 25 if user-invoked);
          model-invoked description has a 'Do not use' boundary clause;
          file <= 150 lines; every numbered phase ('## N.') ends with a '**Done when**' line;
          model-invoked skill has an '## Example' section; no em-dash anywhere;
          a sibling named in the boundary clause has an operative call in the body;
          references/ links resolve; credits block has skill/author/url/license.
Warnings: boundary clause > 25 words; no-op phrases ('be careful', 'think carefully', ...)."""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_LINES, MAX_DESC, MAX_DESC_USER, MAX_BOUNDARY = 150, 70, 25, 25
NOOP = re.compile(r"\b(be careful|think carefully|make sure to|be thorough|as appropriate|where appropriate)\b", re.I)

paths = [pathlib.Path(p) for p in sys.argv[1:]] or sorted(ROOT.glob("skills/*/SKILL.md"))
all_names = {p.parent.name for p in ROOT.glob("skills/*/SKILL.md")}
errors, warnings = [], []

for path in paths:
    rel = path.resolve().relative_to(ROOT) if path.resolve().is_relative_to(ROOT) else path
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        errors.append(f"{rel}: no YAML frontmatter"); continue
    fm, body = m.group(1), m.group(2)
    name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc_m = re.search(r"^description:\s*(.+)$", fm, re.M)
    if not (name_m and desc_m):
        errors.append(f"{rel}: frontmatter lacks name or description"); continue
    name = name_m.group(1).strip()
    desc = desc_m.group(1).strip().strip('"').strip("'")
    user_invoked = re.search(r"^disable-model-invocation:\s*true\s*$", fm, re.M) is not None
    if name != path.parent.name:
        errors.append(f"{rel}: name '{name}' != folder '{path.parent.name}'")

    words = len(desc.split())
    cap = MAX_DESC_USER if user_invoked else MAX_DESC
    if words > cap:
        errors.append(f"{rel}: description is {words} words (max {cap})")

    if not user_invoked:
        parts = re.split(r"\bDo not use\b", desc, maxsplit=1)
        if len(parts) != 2:
            errors.append(f"{rel}: description has no 'Do not use' boundary clause")
        else:
            boundary = parts[1]
            if len(boundary.split()) > MAX_BOUNDARY:
                warnings.append(f"{rel}: boundary clause is {len(boundary.split())} words (aim for <= {MAX_BOUNDARY})")
            for sib in sorted(all_names - {name}):
                if re.search(rf"(?<![\w-]){re.escape(sib)}(?![\w-])", boundary) and f'Call the Skill tool with "{sib}"' not in body:
                    errors.append(f"{rel}: boundary names {sib} but the body has no 'Call the Skill tool with \"{sib}\"' line")
        if not re.search(r"^## (Worked )?[Ee]xamples?\b", body, re.M):
            errors.append(f"{rel}: no '## Example' section")

    total = text.count("\n") + (0 if text.endswith("\n") else 1)
    if total > MAX_LINES:
        errors.append(f"{rel}: {total} lines (max {MAX_LINES})")

    for ln, line in enumerate(text.splitlines(), 1):
        if "—" in line:
            errors.append(f"{rel}:{ln}: em-dash; rewrite with a colon, comma, parentheses, or a new sentence")

    for sec in re.split(r"^(?=## )", body, flags=re.M):
        head = sec.splitlines()[0] if sec.strip() else ""
        if re.match(r"## \d+\.", head) and "**Done when**" not in sec:
            errors.append(f"{rel}: phase '{head}' has no '**Done when**' line")

    for mm in NOOP.finditer(body):
        ln = body[:mm.start()].count("\n") + fm.count("\n") + 3
        warnings.append(f"{rel}:{ln}: no-op phrase '{mm.group(0)}' (delta test)")

    for link in re.findall(r"\]\((references/[^)]+)\)", body):
        if not (path.parent / link).exists():
            errors.append(f"{rel}: link to missing file {link}")

    if re.search(r"^\s*credits:", fm, re.M):
        for key in ("skill", "author", "url", "license"):
            if not re.search(rf"^\s+{key}:\s*\S", fm, re.M):
                errors.append(f"{rel}: credits block lacks '{key}'")

for w in warnings: print("warning:", w)
for e in errors: print("error:", e)
print(f"{len(paths)} skills, {len(errors)} errors, {len(warnings)} warnings")
sys.exit(1 if errors else 0)
