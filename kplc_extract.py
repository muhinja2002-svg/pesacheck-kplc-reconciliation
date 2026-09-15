"""
PesaCheck prototype -- KPLC extraction module (v2, corrected).

Unlike RUPHA (three tables in one PDF, parsed by column position), KPLC's
findings sit inside narrative prose across four separate Auditor-General
reports (two real-text, two OCR'd from scanned pages embedded in KPLC's own
annual reports). This is deliberately a DIFFERENT extraction architecture --
regex against sentence-level patterns, not column position -- because that's
the honest test of whether the method generalizes rather than just replaying
the same table-parsing trick on new numbers.
"""
import re
import csv

SOURCES = {
    "FY2022": "fy2022_oag.txt",
    "FY2023": "fy2023_oag.txt",
    "FY2024": "fy2024_oag_ocr.txt",
    "FY2025": "fy2025_oag_ocr.txt",
}

NUM = r"[\d,]+"


def _to_int(tok):
    return int(tok.replace(",", ""))


def load_text(year):
    with open(SOURCES[year], encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_working_capital(text):
    """'current liabilities of Kshs.X ... exceeded its current assets of ... Kshs.Y by Kshs.Z'"""
    m = re.search(
        rf"exceeded its current assets of\s*\n?Kshs\.{NUM}\s+by\s+Kshs\.({NUM})",
        text,
    )
    if m:
        return _to_int(m.group(1))
    m = re.search(rf"negative working capital of Kshs\.({NUM})", text)
    if m:
        return _to_int(m.group(1))
    # Annexure I real-text phrasing, figures given in KShs Million (not full shillings)
    m = re.search(rf"decreasing from KShs\.({NUM})\s*\n?Million in June 2024 to KShs\.({NUM}) Million in June 2025", text)
    if m:
        return _to_int(m.group(2)) * 1_000_000
    return None


def extract_res_deficit(text):
    m = re.search(rf"Kshs\.({NUM})\s+(?:was in respect of|relate[s]? to a debt due from)\s+Rural\s+Electrification", text)
    if m:
        return _to_int(m.group(1))
    return None


def extract_govt_receivables_total(text):
    m = re.search(rf"amount of Kshs\.({NUM})\s*\n?in respect of receivables from other Government", text)
    return _to_int(m.group(1)) if m else None


def extract_cabinet_disbursement(text):
    m = re.search(rf"[Cc]abinet resolution to disburse\s*\n?Kshs\.({NUM})", text)
    return _to_int(m.group(1)) if m else None


def extract_county_receivables_total(text):
    m = re.search(rf"amount of Kshs\.({NUM})\s+due from County Governments", text)
    if m:
        return _to_int(m.group(1))
    m = re.search(rf"includes Kshs\.({NUM})\s+in respect of unpaid electricity\s*\n?bills from the forty-seven", text)
    return _to_int(m.group(1)) if m else None


def extract_sampled_counties(text):
    m = re.search(rf"ten \(10\) County Governments totalling Kshs\.({NUM})", text)
    return _to_int(m.group(1)) if m else None


def extract_nairobi_variance(text):
    # SEP tolerates OCR noise from the source table's own borders/shading
    # (underscores, pipes, en/em-dashes), confirmed present in the actual
    # OCR of the FY2025 scanned table: 'Nairobi__| _3,603,991,809| ...'
    # -- the original \s+-only separator cannot match through that and
    # silently returned None despite the row being present and legible.
    SEP = r"[\s_|—–-]*"
    m = re.search(rf"Nairobi{SEP}({NUM}){SEP}({NUM}){SEP}({NUM})", text)
    if m:
        return {
            "kplc_claim": _to_int(m.group(1)),
            "confirmed": _to_int(m.group(2)),
            "variance": _to_int(m.group(3)),
        }
    return None


def extract_land_titles(text):
    m = re.search(rf"\((\d+)\)\s+parcels?[^.]*?valued at Kshs\.({NUM})[^.]*?no title deeds", text, re.DOTALL)
    if m:
        return {"count": int(m.group(1)), "value": _to_int(m.group(2))}
    return None


def extract_land_liens(text):
    m = re.search(rf"\((\d+)\)\s+of the parcels were charged for Kshs\.({NUM})", text)
    if m:
        return {"count": int(m.group(1)), "value": _to_int(m.group(2))}
    return None


def extract_kengen_ipp(text):
    # FY2025 phrasing: combined total, not split -- 'purchased ... for a cost of Kshs.X'
    m = re.search(
        rf"purchased a total of\s+[\d,]+ gigawatt-hour \(GWh\) units of electricity for a cost of Kshs\.({NUM})",
        text,
    )
    if m:
        return {"combined_total_cost": _to_int(m.group(1))}
    # FY2022 phrasing: separate KenGen vs IPP cost figures
    # CORRECTED (prior audit): two bugs confirmed against the real FY2022
    # source text. (1) KEN?[Gg]en was case-sensitive and could not match the
    # all-caps "KENGEN" the report actually uses -- fixed with re.IGNORECASE.
    # (2) FY2022 wraps "power purchased" and "from KENGEN" onto separate
    # lines (a page/column line-break) -- fixed with \s+.
    m = re.search(
        rf"Kshs\.({NUM})\s+or\s+\d+%\s*,?\s*compared to (?:the )?purchase\s*\n?cost of power from IPPs totalling Kshs\.({NUM})",
        text,
        re.IGNORECASE,
    )
    if m:
        return {"kengen_cost": _to_int(m.group(1)), "ipp_cost": _to_int(m.group(2))}
    m = re.search(
        rf"cost of the (?:total )?power purchased\s+from KEN?[Gg]en(?: in)? was Kshs\.({NUM})[^.]*?Kshs\.({NUM})",
        text,
        re.IGNORECASE,
    )
    if m:
        return {"kengen_cost": _to_int(m.group(1)), "ipp_cost": _to_int(m.group(2))}
    # FY2023 phrasing: 'was Kshs.X equivalent to Y% compared to power purchase
    # cost of Kshs.Z from IPPs, equivalent to W%'. This is genuinely
    # DIFFERENT wording from FY2022, not just a layout artifact -- confirmed
    # by direct comparison against both source PDFs. FY2023's underlying
    # extraction problem was separate and more fundamental: this paragraph
    # sits in a two-column "Key Audit Matter" table, and plain
    # `pdftotext -layout` interleaves it word-by-word with the adjacent
    # "How My Audit Addressed the Key Audit Matter" column (e.g. "purchased
    # iii. Reviewed invoicing and"), corrupting the figures themselves, not
    # just the surrounding phrasing. No regex can recover data that's been
    # word-interleaved with an unrelated column. Fixed at the SOURCE instead:
    # build_kplc_sources.sh now crops this specific page to its left 55% of
    # page width via pdfplumber before extracting text, isolating this
    # column cleanly. This regex matches that clean, column-isolated text.
    m = re.search(
        rf"Kshs\.({NUM})\s*\n?equivalent to\s+\d+%\s+compared to power purchase\s*\n?cost of\s+Kshs\.({NUM})\s+from IPPs",
        text,
        re.IGNORECASE,
    )
    if m:
        return {"kengen_cost": _to_int(m.group(1)), "ipp_cost": _to_int(m.group(2))}
    return None


def extract_all():
    results = {}
    for year in SOURCES:
        text = load_text(year)
        results[year] = {
            "working_capital_deficit": extract_working_capital(text),
            "govt_receivables_total": extract_govt_receivables_total(text),
            "res_deficit": extract_res_deficit(text),
            "cabinet_disbursement": extract_cabinet_disbursement(text),
            "county_receivables_total": extract_county_receivables_total(text),
            "sampled_counties_variance": extract_sampled_counties(text),
            "nairobi": extract_nairobi_variance(text),
            "land_titles": extract_land_titles(text),
            "land_liens": extract_land_liens(text),
            "kengen_ipp": extract_kengen_ipp(text),
        }
    return results


def load_ground_truth(path="kplc_findings_dataset.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    results = extract_all()
    for year, r in results.items():
        print(f"\n{year}:")
        for k, v in r.items():
            print(f"  {k}: {v}")
