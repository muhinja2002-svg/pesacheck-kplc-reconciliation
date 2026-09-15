"""
PesaCheck prototype -- Stage 3: narrative-absence check.
 
This is the actual thesis of the RUPHA/KPLC reconciliation series: a finding
can be real, disclosed, and audited -- and still not surface in the section
most readers (including AGM voters) actually read. Extraction proves a
figure exists in the OAG report; this stage proves whether the SAME figure
also appears in KPLC's own shareholder-facing narrative (Chairman's Message,
MD/CEO's Message, Financial/Operational Highlights).
 
Only run for FY2024 and FY2025, since those are the only years the narrative
document (Document B) was uploaded -- FY2022/FY2023 annual reports were not
provided, matching the scope Rawlings' own methodology memo already disclosed.
"""
import re
from kplc_extract import extract_all, load_ground_truth
 
NARRATIVE_WINDOWS = {
    # (file, start_line, end_line) -- Chairman's Message + MD/CEO's Message +
    # Financial/Operational Highlights, ending well before the embedded
    # (scanned) OAG report section in each PDF.
    "FY2024": ("fy2024_annual_report.txt", 1, 5000),
    "FY2025": ("fy2025_annual_report.txt", 1, 4400),
}
 
 
def load_narrative(year):
    fname, start, end = NARRATIVE_WINDOWS[year]
    with open(fname, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    return "".join(lines[start - 1:end])
 
 
def _num_variants(n):
    """Generate plausible printed forms of a figure: full comma form (safe,
    specific), and billion/million-rounded forms PAIRED WITH a currency/unit
    marker regex (not bare digits, which false-match unrelated numbers like
    percentages or section labels -- see 95.74% / '8.1.2.3' false positives
    caught during testing)."""
    variants = [("literal", f"{n:,}")]
    if n >= 1_000_000_000:
        b = n / 1_000_000_000
        variants.append(("regex", rf"[Kk][Ss]hs\.?\s*{b:.1f}\s*[Bb](?:illion)?"))
    elif n >= 1_000_000:
        m = n / 1_000_000
        variants.append(("regex", rf"[Kk][Ss]hs\.?\s*{m:.1f}\s*[Mm](?:illion)?"))
    return variants
 
 
def check_presence(narrative_text, value):
    if value is None:
        return "n/a"
    for kind, v in _num_variants(value):
        if kind == "literal" and v in narrative_text:
            return f"FOUND (matched '{v}')"
        if kind == "regex" and re.search(v, narrative_text):
            m = re.search(v, narrative_text)
            return f"FOUND (matched '{m.group(0)}')"
    return "No"
 
 
REFRAME_KEYWORDS = ["improv", "resurgence", "renewed confidence", "strengthen", "sustainab"]
 
 
def check_reframe(narrative_text, topic_keywords):
    """Even when the figure is absent, check whether the TOPIC is mentioned
    in softened/positive language -- this is the 'reframed as improvement'
    pattern the ground truth already documents for working capital."""
    hits = []
    for kw in topic_keywords:
        for m in re.finditer(re.escape(kw), narrative_text, re.IGNORECASE):
            window = narrative_text[max(0, m.start() - 150):m.start() + 150]
            if any(rk in window.lower() for rk in REFRAME_KEYWORDS):
                hits.append(kw)
                break
    return hits
 
 
CHECKS = {
    # finding label -> (extractor field path, topic keywords for reframe check)
    "Negative working capital": (lambda r: r["working_capital_deficit"], ["working capital"]),
    "Government receivables - RES deficit": (lambda r: r["res_deficit"], ["rural electrification", "res "]),
    "County government receivables - total": (lambda r: r["county_receivables_total"], ["county government"]),
    "County government receivables - Nairobi variance": (lambda r: r["nairobi"]["variance"] if r["nairobi"] else None, ["nairobi"]),
    "Land without title deeds": (lambda r: r["land_titles"]["value"] if r["land_titles"] else None, ["title deed"]),
    "KenGen vs IPP cost disparity": (lambda r: r["kengen_ipp"]["combined_total_cost"] if r["kengen_ipp"] else None, ["kengen"]),
}
 
 
def main():
    extracted = extract_all()
    gt_rows = load_ground_truth()
    gt_lookup = {(r["finding"], r["fiscal_year"]): r["in_shareholder_narrative"] for r in gt_rows}
 
    print("=" * 78)
    print("NARRATIVE-ABSENCE CHECK -- does the extracted OAG figure also appear")
    print("in KPLC's own shareholder-facing narrative? (FY2024, FY2025 only)")
    print("=" * 78)
 
    for year in ("FY2024", "FY2025"):
        narrative = load_narrative(year)
        print(f"\n--- {year} ---")
        for finding, (getter, keywords) in CHECKS.items():
            value = getter(extracted[year])
            presence = check_presence(narrative, value)
            gt_claim = gt_lookup.get((finding, year), "(not in ground truth for this year)")
            line = f"  {finding}: tool says narrative={presence}"
            if presence == "No":
                reframe_hits = check_reframe(narrative, keywords)
                if reframe_hits:
                    line += f" -- BUT topic discussed nearby positive language (possible reframe, keyword: {reframe_hits[0]})"
            line += f"  | ground truth says: '{gt_claim}'"
            print(line)
 
 
if __name__ == "__main__":
    main()
 
