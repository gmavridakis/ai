# install.ps1 — link ~/.claude/skills to this repo's skills/ folder and wire the index import.
# Idempotent. No admin needed (junction, not symlink). Never deletes user data.
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'
$repoSkills = Join-Path $PSScriptRoot 'skills'
$claudeDir  = Join-Path $HOME '.claude'
$link       = Join-Path $claudeDir 'skills'
$claudeMd   = Join-Path $claudeDir 'CLAUDE.md'
$importLine = '@~/.claude/skills/INDEX.md'
$globLine   = '@~/.claude/skills/*/SKILL.md'

if (-not (Test-Path $repoSkills)) { throw "skills/ not found next to install.ps1 ($repoSkills)" }
New-Item -ItemType Directory -Force -Path $claudeDir | Out-Null

# --- Invariant A: link, don't copy -------------------------------------------
$item = Get-Item -LiteralPath $link -ErrorAction SilentlyContinue
if ($item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    $target = (Get-Item -LiteralPath $link).Target
    if ($target -and ((Resolve-Path $target).Path -eq (Resolve-Path $repoSkills).Path)) {
        Write-Host "OK   ~/.claude/skills already links to $repoSkills"
    } else {
        Write-Host "FIX  ~/.claude/skills links to '$target'; relinking (old link removed, target untouched)"
        # Remove only the reparse point, never its target.
        [IO.Directory]::Delete($link)
        New-Item -ItemType Junction -Path $link -Target $repoSkills | Out-Null
    }
} elseif ($item) {
    # Real directory: adopt any skill folders the repo lacks, back the rest up, then link.
    $n = 1; while (Test-Path "$link.bak-$n") { $n++ }
    $bak = "$link.bak-$n"
    Get-ChildItem -LiteralPath $link -Directory | ForEach-Object {
        $dest = Join-Path $repoSkills $_.Name
        if ((Test-Path (Join-Path $_.FullName 'SKILL.md')) -and -not (Test-Path $dest)) {
            Copy-Item -Recurse -LiteralPath $_.FullName -Destination $dest
            Write-Host "ADOPT copied stray skill '$($_.Name)' into repo skills/ (commit it)"
        }
    }
    Move-Item -LiteralPath $link -Destination $bak
    Write-Host "BAK  moved real directory ~/.claude/skills to $bak"
    New-Item -ItemType Junction -Path $link -Target $repoSkills | Out-Null
    Write-Host "LINK ~/.claude/skills -> $repoSkills"
} else {
    New-Item -ItemType Junction -Path $link -Target $repoSkills | Out-Null
    Write-Host "LINK ~/.claude/skills -> $repoSkills"
}

# --- Invariant B: one index import, never a glob -----------------------------
$lines = @()
if (Test-Path $claudeMd) { $lines = @(Get-Content -LiteralPath $claudeMd) }
$before = $lines.Count
$lines = @($lines | Where-Object { $_.Trim() -ne $globLine })
if ($lines.Count -ne $before) { Write-Host "FIX  removed glob import '$globLine' from CLAUDE.md (glob imports do not expand)" }
$hits = @($lines | Where-Object { $_.Trim() -eq $importLine })
if ($hits.Count -eq 0) {
    $lines += $importLine
    Write-Host "FIX  added '$importLine' to CLAUDE.md"
} elseif ($hits.Count -gt 1) {
    $seen = $false
    $lines = @($lines | Where-Object { if ($_.Trim() -eq $importLine) { if ($seen) { $false } else { $seen = $true; $true } } else { $true } })
    Write-Host "FIX  de-duplicated '$importLine' in CLAUDE.md"
} else {
    Write-Host "OK   CLAUDE.md imports $importLine exactly once"
}
Set-Content -LiteralPath $claudeMd -Value $lines -Encoding UTF8
Write-Host "DONE skills are live in the next Claude session."
