#!/usr/bin/env python3
"""
fetch_sources.py — Προσωπικό εργαλείο τοπικής ανάγνωσης ειδήσεων.

ΣΗΜΑΝΤΙΚΟ: Αυτό το script είναι αποκλειστικά για προσωπική χρήση, τοπικά στον
υπολογιστή σου. Δεν το τρέχει, δεν το διαβάζει και δεν το χρησιμοποιεί κανένα
Claude/Cowork session ή scheduled task (ούτε το Daily Brief). Δεν είναι μέρος
κανενός automation pipeline -- είναι ένα ανεξάρτητο εργαλείο που τρέχεις μόνος
σου, όποτε θες, για να διαβάζεις πιο γρήγορα πηγές που σε ενδιαφέρουν.

Τι κάνει:
  - Κάνει fetch την homepage κάθε πηγής στη λίστα SOURCES παρακάτω.
  - Εξάγει τον τίτλο της σελίδας + μια λίστα πιθανών τίτλων άρθρων
    (heuristic: κείμενο μέσα σε <a> tags με μήκος >= MIN_HEADLINE_LEN).
  - Γράφει τα πάντα σε ένα Markdown αρχείο, με ένα "## " header ανά πηγή.

Εγκατάσταση (μία φορά, σε Command Prompt / PowerShell / terminal):
    pip install requests beautifulsoup4

Χρήση:
    python fetch_sources.py
    (γράφει output σε ./fetched/fetched-YYYY-MM-DD.md, στον φάκελο απ' όπου
    τρέχεις το script)

Περιορισμοί που αξίζει να ξέρεις:
  - Πολλά news sites απαγορεύουν automated scraping στους Terms of Service
    τους. Η χρήση του για προσωπική ανάγνωση είναι δική σου απόφαση/ευθύνη.
  - Μερικά sites (ιδίως με Cloudflare/bot-protection ή πλήρως JS-rendered
    περιεχόμενο, π.χ. bbc.com, nytimes.com) μπορεί να μπλοκάρουν ή να μην
    επιστρέψουν χρήσιμο περιεχόμενο με απλό requests+BeautifulSoup. Το script
    απλά θα αναφέρει σφάλμα/κενό αποτέλεσμα για εκείνη την πηγή και θα
    συνεχίσει με τις υπόλοιπες -- δεν σταματάει όλο το run.
  - Η εξαγωγή τίτλων είναι ένα απλό heuristic (μεγάλα <a> links), όχι πλήρης
    εξαγωγή άρθρου. Αν θες πιο "καθαρή" εξαγωγή κειμένου άρθρου, θα χρειαστεί
    κάτι πιο προηγμένο (π.χ. trafilatura/readability, ή Playwright για
    JS-heavy σελίδες) -- πες μου αν θες να το επεκτείνω.
  - Για να προσθέσεις/αφαιρέσεις πηγές, επεξεργάσου απλά τη λίστα SOURCES.
"""

import os
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SOURCES = [
    ("Καθημερινή", "https://www.kathimerini.gr"),
    ("ΕΡΤ News", "https://www.ertnews.gr"),
    ("in.gr", "https://www.in.gr"),
    ("Τα Νέα", "https://www.tanea.gr"),
    ("News247", "https://www.news247.gr"),
    ("CNN Greece", "https://www.cnn.gr"),
    ("ΑΠΕ-ΜΠΕ", "https://www.amna.gr"),
    ("Gazzetta", "https://www.gazzetta.gr"),
    ("SDNA", "https://www.sdna.gr"),
    ("Reuters", "https://www.reuters.com"),
    ("AP", "https://apnews.com"),
    ("BBC", "https://www.bbc.com/news"),
    ("DW", "https://www.dw.com"),
    ("The Guardian", "https://www.theguardian.com"),
    ("Al Jazeera", "https://www.aljazeera.com"),
    ("France24", "https://www.france24.com"),
    ("FT", "https://www.ft.com"),
    ("Economist", "https://www.economist.com"),
    ("WSJ", "https://www.wsj.com"),
    ("Bloomberg", "https://www.bloomberg.com"),
    ("Politico Europe", "https://www.politico.eu"),
    ("Euractiv", "https://www.euractiv.com"),
    ("NYT", "https://www.nytimes.com"),
    ("MIT Technology Review", "https://www.technologyreview.com"),
    ("Nature", "https://www.nature.com"),
    ("Science News", "https://www.sciencenews.org"),
    ("Ars Technica", "https://arstechnica.com"),
    ("The Verge", "https://www.theverge.com"),
    ("Wired", "https://www.wired.com"),
    ("Vox", "https://www.vox.com"),
    ("Transfermarkt", "https://www.transfermarkt.com"),
    ("ESPN", "https://www.espn.com"),
    ("Sky Sports", "https://www.skysports.com"),
    ("The Athletic", "https://www.nytimes.com/athletic"),
    ("AFP Fact Check", "https://factcheck.afp.com"),
    ("Reuters Fact Check", "https://www.reuters.com/fact-check"),
]

OUTPUT_DIR = "fetched"
MIN_HEADLINE_LEN = 25
MAX_HEADLINES_PER_SOURCE = 15
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 1.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def extract_headlines(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "(χωρίς τίτλο)"

    seen = set()
    headlines = []
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        href = a.get("href", "")
        if not text or len(text) < MIN_HEADLINE_LEN:
            continue
        if text in seen:
            continue
        seen.add(text)
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        headlines.append((text, href))
        if len(headlines) >= MAX_HEADLINES_PER_SOURCE:
            break

    return title, headlines


def fetch_source(name, url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        title, headlines = extract_headlines(resp.text, url)
        return {"ok": True, "title": title, "headlines": headlines}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(OUTPUT_DIR, f"fetched-{today}.md")

    lines = [f"# Fetched sources — {today}", ""]

    for name, url in SOURCES:
        print(f"Fetching {name} ({url})...")
        result = fetch_source(name, url)
        lines.append(f"## {name}")
        lines.append(f"Πηγή: {url}")
        lines.append("")
        if result["ok"]:
            if result["headlines"]:
                for text, href in result["headlines"]:
                    lines.append(f"- [{text}]({href})")
            else:
                lines.append("_(δεν βρέθηκαν τίτλοι άρθρων — πιθανόν JS-rendered σελίδα)_")
        else:
            lines.append(f"_(απέτυχε: {result['error']})_")
        lines.append("")
        time.sleep(DELAY_BETWEEN_REQUESTS)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nΈτοιμο: {out_path}")


if __name__ == "__main__":
    main()
