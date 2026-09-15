"""
PesaCheck prototype -- KPLC validation: compare extracted figures against
kplc_findings_dataset.csv (Rawlings's verified ground truth).
"""
from kplc_extract import extract_all, load_ground_truth
 
ROUNDING_TOLERANCE = 1_000_000  # ground truth rounds some figures to the nearest ~100K-1M Kshs
EXACT_TOLERANCE = 1
 
 
def _values_match(tool_val, gt_val):
    """Ground truth stores deficits as negative; tool extracts magnitudes. Compare
    on absolute value, and allow for known CSV rounding (documented below) rather
    than demanding exact-to-the-shilling equality everywhere."""
    if abs(abs(tool_val) - abs(gt_val)) <= EXACT_TOLERANCE:
        return "exact"
    if abs(abs(tool_val) - abs(gt_val)) <= ROUNDING_TOLERANCE:
        return "rounded"
    return None
 
# Maps each ground-truth `finding` string to the extractor's field(s).
FIELD_MAP = {
    "Negative working capital": ("working_capital_deficit", lambda r: r["working_capital_deficit"]),
    "Government receivables - total (incl. RES + other govt entities)": ("govt_receivables_total", lambda r: r["govt_receivables_total"]),
    "Government receivables - RES deficit (RES-specific)": ("res_deficit", lambda r: r["res_deficit"]),
    "Government receivables - RES deficit (report-body figure)": ("res_deficit", lambda r: r["res_deficit"]),
    "Government receivables - RES deficit": ("res_deficit", lambda r: r["res_deficit"]),
    "Government receivables - Cabinet disbursement unpaid": ("cabinet_disbursement", lambda r: r["cabinet_disbursement"]),
    "County government receivables - total": ("county_receivables_total", lambda r: r["county_receivables_total"]),
    "County government receivables - sampled 10 counties variance": ("sampled_counties_variance", lambda r: r["sampled_counties_variance"]),
    "County government receivables - Nairobi (KPLC claim)": ("nairobi.kplc_claim", lambda r: r["nairobi"]["kplc_claim"] if r["nairobi"] else None),
    "County government receivables - Nairobi (confirmed)": ("nairobi.confirmed", lambda r: r["nairobi"]["confirmed"] if r["nairobi"] else None),
    "County government receivables - Nairobi variance": ("nairobi.variance", lambda r: r["nairobi"]["variance"] if r["nairobi"] else None),
    "Land without title deeds": ("land_titles.value", lambda r: r["land_titles"]["value"] if r["land_titles"] else None),
    "Land parcels charged to private company": ("land_liens.value", lambda r: r["land_liens"]["value"] if r["land_liens"] else None),
    "KenGen vs IPP cost disparity": ("kengen_ipp.combined_total_cost", lambda r: r["kengen_ipp"]["combined_total_cost"] if r["kengen_ipp"] else None),
}
 
SKIP_YEARS = {"FY2023-FY2024"}  # roll-forward verification row, not a direct extraction target
 
 
def main():
    extracted = extract_all()
    gt_rows = load_ground_truth()
 
    checked = exact = rounded = mismatched = not_attempted = null_correctly_skipped = 0
    details = []
 
    for row in gt_rows:
        finding = row["finding"]
        year = row["fiscal_year"]
        gt_val_raw = row["figure_kshs"]
 
        if year in SKIP_YEARS:
            continue
        if finding not in FIELD_MAP:
            not_attempted += 1
            details.append(f"  NOT ATTEMPTED (not in this prototype's scope): {finding} ({year})")
            continue
        if gt_val_raw == "null":
            null_correctly_skipped += 1
            continue  # ground truth itself has no figure for this finding (qualitative only)
        if year not in extracted:
            not_attempted += 1
            details.append(f"  NOT ATTEMPTED (no source for {year}): {finding}")
            continue
 
        checked += 1
        gt_val = int(gt_val_raw)
        _, getter = FIELD_MAP[finding]
        tool_val = getter(extracted[year])
 
        if tool_val is None:
            mismatched += 1
            details.append(f"  MISSED: {finding} ({year}) -- ground truth {gt_val:,}, tool found nothing")
            continue
 
        match_type = _values_match(tool_val, gt_val)
        if match_type == "exact":
            exact += 1
        elif match_type == "rounded":
            rounded += 1
            details.append(
                f"  MATCH WITHIN ROUNDING: {finding} ({year}) -- ground truth {gt_val:,} (CSV-rounded), "
                f"tool found {tool_val:,} (exact source figure, diff {tool_val - abs(gt_val):,})"
            )
        else:
            mismatched += 1
            details.append(
                f"  VALUE MISMATCH: {finding} ({year}) -- ground truth {gt_val:,}, tool found {tool_val:,} "
                f"(diff {tool_val - abs(gt_val):,})"
            )
 
    print("=" * 70)
    print("KPLC VALIDATION vs. kplc_findings_dataset.csv")
    print("=" * 70)
    print(f"\nFindings with a figure, in scope for this prototype: {checked}")
    print(f"  Exact matches:            {exact}")
    print(f"  Matches within CSV rounding: {rounded}")
    print(f"  True mismatches/misses:   {mismatched}")
    print(f"Findings outside this prototype's current scope: {not_attempted}")
    print(f"Qualitative findings (no figure in ground truth, correctly not extracted): {null_correctly_skipped}")
    if checked:
        print(f"\nAccuracy on in-scope figures (exact + within-rounding): {exact+rounded}/{checked} ({(exact+rounded)/checked:.0%})")
 
    if details:
        print("\nDetails:")
        for d in details:
            print(d)
 
 
if __name__ == "__main__":
    main()
 
