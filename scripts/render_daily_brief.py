#!/usr/bin/env python3
"""
Renders the Daily News Brief markdown (daily-news/latest.md) into a
self-contained, email-safe HTML document (table-based layout, inline CSS)
for sending via dawidd6/action-send-mail's `html_body` input.

Usage: python3 render_daily_brief.py <input.md> <output.html>

Design notes:
- Pure, deterministic post-processing of markdown -> HTML. No LLM involved,
  so this never adds to the scheduled agent's time budget or failure risk.
- Section color-coding is matched on stable substrings of the fixed Greek
  section headings the Daily Brief prompt always uses. Any heading that
  doesn't match falls back to a neutral style instead of crashing, so a
  future wording tweak degrades gracefully rather than breaking the email.
"""
import sys
import re
import datetime
import markdown
from bs4 import BeautifulSoup, NavigableString

GREEK_MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου",
                "Ιουλίου", "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]
GREEK_WEEKDAYS = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]

# (substring to match in the h2 text, accent color, light tint background)
SECTION_STYLES = [
    ("Πολιτική & Οικονομία", "#1d4ed8", "#eff6ff"),
    ("Διεθνή",               "#0d9488", "#f0fdfa"),
    ("Τεχνολογία",           "#6d28d9", "#f5f3ff"),
    ("Trends",               "#b45309", "#fffbeb"),
    ("Ολυμπιακός",           "#dc2626", "#fef2f2"),
    ("Εθνική Ελλάδας",       "#1e3a8a", "#eef2ff"),
    ("Έλληνες στο εξωτερικό", "#334155", "#f8fafc"),
    ("Καιρός",               "#0ea5e9", "#f0f9ff"),
]
DEFAULT_STYLE = ("#475569", "#f8fafc")

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def section_style(heading_text):
    for key, color, tint in SECTION_STYLES:
        if key in heading_text:
            return color, tint
    return DEFAULT_STYLE


def pretty_date(h1_text):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", h1_text)
    if not m:
        return h1_text.lstrip("# ").strip()
    d, mo, y = (int(x) for x in m.groups())
    try:
        dt = datetime.date(y, mo, d)
        return f"{GREEK_WEEKDAYS[dt.weekday()]}, {d} {GREEK_MONTHS[mo - 1]} {y}"
    except ValueError:
        return h1_text.lstrip("# ").strip()


def inner_html(tag):
    return "".join(
        c if isinstance(c, NavigableString) else str(c) for c in tag.contents
    ).strip()


def item_card(tag, accent):
    html = inner_html(tag)
    is_warning = html.lstrip().startswith("⚠️") or html.lstrip().startswith("⚠")
    if is_warning:
        bg, border, bar = "#fffbeb", "#fde68a", "#d97706"
    else:
        bg, border, bar = "#ffffff", "#e5e7eb", accent
    return f'''<tr><td style="padding:0 0 10px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{bg};border:1px solid {border};border-radius:8px;">
    <tr>
      <td width="4" style="background:{bar};border-radius:8px 0 0 8px;">&nbsp;</td>
      <td style="padding:12px 16px;font-family:{FONT};font-size:14.5px;line-height:1.55;color:#1f2937;">
        {html}
      </td>
    </tr>
  </table>
</td></tr>'''


def footer_row(tag, is_note=False):
    html = inner_html(tag)
    if is_note:
        return f'''<tr><td style="padding:14px 0 10px 0;font-family:{FONT};font-size:12.5px;color:#9ca3af;text-align:center;">{html}</td></tr>'''
    return f'''<tr><td style="padding:0 0 8px 0;font-family:{FONT};font-size:12px;line-height:1.7;color:#64748b;">{html}</td></tr>'''


def render(md_text):
    html = markdown.markdown(md_text, extensions=["nl2br"])
    soup = BeautifulSoup(html, "html.parser")

    title_date = "Daily Brief"
    body_rows = []
    footer_rows = []
    in_footer = False
    current_accent = DEFAULT_STYLE[0]
    section_count = 0
    item_count = 0
    open_section = False

    def close_section():
        nonlocal open_section
        if open_section:
            body_rows.append("</table></td></tr>")
            open_section = False

    for el in soup.find_all(recursive=False):
        name = el.name
        if name == "h1":
            title_date = pretty_date(el.get_text())
            continue
        if name == "hr":
            close_section()
            in_footer = True
            continue
        if name == "h2":
            close_section()
            heading_text = el.get_text()
            accent, tint = section_style(heading_text)
            current_accent = accent
            section_count += 1
            body_rows.append(
                f'''<tr><td style="padding:22px 0 10px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="border-bottom:2px solid {accent};padding-bottom:6px;">
      <span style="font-family:{FONT};font-size:16px;font-weight:700;color:{accent};">{el.decode_contents()}</span>
    </td></tr>
  </table>
</td></tr>'''
            )
            body_rows.append('<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">')
            open_section = True
            continue
        if name == "h3" and in_footer:
            footer_rows.append(
                f'''<tr><td style="padding:16px 0 6px 0;font-family:{FONT};font-size:13px;font-weight:700;color:#475569;">{el.decode_contents()}</td></tr>'''
            )
            continue
        if name == "p":
            text = el.get_text()
            if not text.strip():
                continue
            if in_footer:
                is_note = text.strip().startswith("Πηγές που ελέγχθηκαν")
                footer_rows.append(footer_row(el, is_note=is_note))
            else:
                item_count += 1
                body_rows.append(item_card(el, current_accent))
            continue
        # Fallback for any other block type (ul/ol/etc.) - render as a card/footer row
        if in_footer:
            footer_rows.append(footer_row(el))
        else:
            item_count += 1
            body_rows.append(item_card(el, current_accent))

    close_section()

    summary_bits = f"{item_count} ενημερώσεις &middot; {section_count} ενότητες"

    doc = f"""<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Brief</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;">
<tr><td align="center" style="padding:20px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:10px;overflow:hidden;">
<tr><td style="background:#0f172a;padding:22px 24px;">
  <div style="font-family:{FONT};font-size:20px;font-weight:700;color:#ffffff;">🇬🇷 Daily Brief</div>
  <div style="font-family:{FONT};font-size:13.5px;color:#cbd5e1;margin-top:4px;">{title_date}</div>
  <div style="font-family:{FONT};font-size:12px;color:#94a3b8;margin-top:8px;">{summary_bits}</div>
</td></tr>
<tr><td style="padding:4px 24px 8px 24px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  {"".join(body_rows)}
  </table>
</td></tr>
<tr><td style="padding:4px 24px 22px 24px;border-top:1px solid #e5e7eb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  {"".join(footer_rows)}
  </table>
</td></tr>
</table>
<div style="font-family:{FONT};font-size:11px;color:#94a3b8;padding:14px 8px;max-width:600px;">
  Αυτόματο ημερήσιο brief &middot; δημιουργήθηκε από το scheduled task "Daily News Brief"
</div>
</td></tr>
</table>
</body>
</html>"""
    return doc


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: render_daily_brief.py <input.md> <output.html>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        md_text = f.read()
    out = render(md_text)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {sys.argv[2]} ({len(out)} bytes)")
