#!/usr/bin/env sh
# install.sh — link ~/.claude/skills to this repo's skills/ folder and wire the index import.
# Idempotent. Never deletes user data.   sh ./install.sh
set -eu
repo_skills="$(cd "$(dirname "$0")" && pwd)/skills"
claude_dir="$HOME/.claude"
link="$claude_dir/skills"
claude_md="$claude_dir/CLAUDE.md"
import_line='@~/.claude/skills/INDEX.md'
glob_line='@~/.claude/skills/*/SKILL.md'

[ -d "$repo_skills" ] || { echo "skills/ not found next to install.sh" >&2; exit 1; }
mkdir -p "$claude_dir"

# --- Invariant A: link, don't copy -------------------------------------------
if [ -L "$link" ]; then
  if [ "$(cd "$link" && pwd -P)" = "$(cd "$repo_skills" && pwd -P)" ]; then
    echo "OK   ~/.claude/skills already links to $repo_skills"
  else
    echo "FIX  ~/.claude/skills pointed elsewhere; relinking (old link removed, target untouched)"
    rm "$link"; ln -s "$repo_skills" "$link"
  fi
elif [ -d "$link" ]; then
  n=1; while [ -e "$link.bak-$n" ]; do n=$((n+1)); done
  for d in "$link"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    name="$(basename "$d")"
    if [ ! -d "$repo_skills/$name" ]; then
      cp -R "$d" "$repo_skills/$name"
      echo "ADOPT copied stray skill '$name' into repo skills/ (commit it)"
    fi
  done
  mv "$link" "$link.bak-$n"; echo "BAK  moved real directory ~/.claude/skills to $link.bak-$n"
  ln -s "$repo_skills" "$link"; echo "LINK ~/.claude/skills -> $repo_skills"
else
  ln -s "$repo_skills" "$link"; echo "LINK ~/.claude/skills -> $repo_skills"
fi

# --- Invariant B: one index import, never a glob -----------------------------
touch "$claude_md"
tmp="$(mktemp)"
if grep -qxF "$glob_line" "$claude_md"; then
  grep -vxF "$glob_line" "$claude_md" > "$tmp" || true; cat "$tmp" > "$claude_md"
  echo "FIX  removed glob import '$glob_line' from CLAUDE.md (glob imports do not expand)"
fi
count="$(grep -cxF "$import_line" "$claude_md" || true)"
if [ "$count" -eq 0 ]; then
  printf '%s\n' "$import_line" >> "$claude_md"; echo "FIX  added '$import_line' to CLAUDE.md"
elif [ "$count" -gt 1 ]; then
  awk -v l="$import_line" '$0==l{ if (seen++) next } {print}' "$claude_md" > "$tmp"; cat "$tmp" > "$claude_md"
  echo "FIX  de-duplicated '$import_line' in CLAUDE.md"
else
  echo "OK   CLAUDE.md imports $import_line exactly once"
fi
rm -f "$tmp"
echo "DONE skills are live in the next Claude session."
