#!/usr/bin/env bash
# build_kplc_sources.sh
#
# Regenerates the six intermediate text files kplc_extract.py and
# kplc_narrative_check.py depend on (fy2022_oag.txt, fy2023_oag.txt,
# fy2024_oag_ocr.txt, fy2025_oag_ocr.txt, fy2024_annual_report.txt,
# fy2025_annual_report.txt), none of which were part of the original
# project upload set -- PROJECT_SETUP.md lists the four source PDFs, but
# not the derived .txt files the code actually reads. That gap means the
# reported 95% KPLC accuracy figure could not be reproduced by a fresh
# session without first reverse-engineering how those six files were
# built. This script is that missing step, written up during the audit
# pass that had to reconstruct it from scratch.
#
# Requires: poppler-utils (pdftotext, pdftoppm), tesseract-ocr, python3+Pillow
# Run from a directory containing the four source PDFs (see PROJECT_SETUP.md).
set -euo pipefail

FY2022_PDF="Kenya-Power-Lighting-Company-2021-2022.pdf"      # oagkenya.go.ke, verified byte-identical to the live copy during this audit
FY2023_PDF="Kenya-Power-and-Lighting-Company.pdf"            # oagkenya.go.ke, verified byte-identical to the live copy during this audit
FY2024_PDF="01JDRPZS8NZ473CWE2XCSQ1REJ.pdf"                  # FY2023/24 Integrated Annual Report
FY2025_PDF="01KB4JTB49DXJ81DG79JVEE0M3.pdf"                  # FY2025 Integrated Annual Report

echo "== FY2022 / FY2023: real-text OAG reports, direct extraction =="
pdftotext -layout "$FY2022_PDF" fy2022_oag.txt
pdftotext -layout "$FY2023_PDF" fy2023_oag.txt

echo "== FY2023: fix two-column Key Audit Matter page interleaving =="
# The page containing "Comparative Cost of Power Purchase between KenGen and
# Independent Power Producers" is a two-column table (Key Audit Matter | How
# My Audit Addressed the Key Audit Matter). `pdftotext -layout` merges the
# two columns word-by-word on lines where the left column runs long enough
# to abut the right ("...power purchased iii. Reviewed invoicing and"),
# corrupting the KenGen/IPP cost figures themselves -- not just the
# surrounding phrasing, so no regex on the merged text can recover them.
# Fixed by re-extracting just this page, cropped to its left column, with
# pdfplumber (which preserves per-word coordinates, unlike pdftotext).
# Diagnosed and fixed during the second audit pass, 2026-08-27.
python3 - "$FY2023_PDF" << 'PYEOF'
import sys, re
import pdfplumber

pdf_path = sys.argv[1]
pdf = pdfplumber.open(pdf_path)
target_page = None
for i, page in enumerate(pdf.pages):
    text = page.extract_text() or ""
    if "Comparative Cost of Power Purchase" in text and "How My Audit Addressed" in text:
        target_page = i
        break

if target_page is None:
    print("WARNING: could not locate the two-column KenGen/IPP page for column-aware re-extraction; fy2023_oag.txt left as plain pdftotext output.", file=sys.stderr)
else:
    page = pdf.pages[target_page]
    w, h = page.width, page.height
    clean_left_column = page.crop((0, 0, w * 0.55, h)).extract_text()

    with open("fy2023_oag.txt", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    # Splice the clean column text in immediately after the interleaved
    # version, rather than trying to locate-and-replace the corrupted block
    # by line range (fragile against pdftotext version differences). The
    # extraction regex in kplc_extract.py does a plain re.search, so the
    # clean copy further down the file is what actually matches.
    marker = "Comparative Cost of Power Purchase"
    insert_at = full_text.find(marker)
    if insert_at != -1:
        # Insert after the full interleaved page's likely end (next
        # "Report of the Auditor-General" footer, which starts every page).
        next_footer = full_text.find("Report of the Auditor-General", insert_at)
        insert_at = next_footer if next_footer != -1 else len(full_text)
        full_text = (
            full_text[:insert_at]
            + "\n\n[COLUMN-AWARE RE-EXTRACTION of the KenGen/IPP Key Audit Matter, "
            + "left column only -- see build_kplc_sources.sh]\n"
            + clean_left_column
            + "\n\n"
            + full_text[insert_at:]
        )
        with open("fy2023_oag.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"Fixed: spliced clean column-{target_page+1} text into fy2023_oag.txt")
    else:
        print("WARNING: marker text not found in fy2023_oag.txt after pdftotext extraction; skipping splice.", file=sys.stderr)
PYEOF

echo "== FY2024 / FY2025: full narrative text (for the narrative-absence check) =="
pdftotext -layout "$FY2024_PDF" fy2024_annual_report.txt
pdftotext -layout "$FY2025_PDF" fy2025_annual_report.txt

echo "== FY2024: OCR the embedded, scanned OAG section (pages 133-149) =="
# This PDF scans one printed page per PDF leaf -- plain per-page OCR is fine.
rm -rf _ocr_fy2024 && mkdir _ocr_fy2024
pdftoppm -f 133 -l 149 -r 300 -png "$FY2024_PDF" _ocr_fy2024/page
: > fy2024_oag_ocr.txt
for f in _ocr_fy2024/page-*.png; do
  tesseract "$f" - --psm 6 2>/dev/null >> fy2024_oag_ocr.txt
  echo "" >> fy2024_oag_ocr.txt
done

echo "== FY2025: OCR the embedded, scanned OAG section (pages 122-130) =="
# NOTE: this step runs 18 separate tesseract calls (9 leaves x 2 halves)
# at 300dpi and takes several minutes end to end -- in a time-limited
# shell (e.g. a sandboxed tool-call budget) run it in the background or
# split the loop below into batches rather than expecting it inline.
# IMPORTANT: unlike the FY2024 PDF, each leaf of THIS PDF is a two-page
# spread (two printed pages scanned side by side into one image). Running
# tesseract on the whole leaf interleaves both pages' text and breaks
# reading order badly enough that several figures (e.g. the Nairobi
# receivables-variance table) fail to extract at all. Each leaf must be
# split into left/right halves BEFORE OCR. This was diagnosed during this
# audit pass by visually inspecting the rasterized pages -- see
# AUDIT_REPORT.md, RUPHA/KPLC Step 4(c) and (e).
rm -rf _ocr_fy2025 && mkdir _ocr_fy2025
pdftoppm -f 122 -l 130 -r 300 -png "$FY2025_PDF" _ocr_fy2025/page
python3 - << 'PYEOF'
from PIL import Image
import glob, os
for fp in sorted(glob.glob('_ocr_fy2025/page-*.png')):
    img = Image.open(fp)
    w, h = img.size
    base = os.path.splitext(os.path.basename(fp))[0]
    img.crop((0, 0, w // 2, h)).save(f'_ocr_fy2025/{base}_a_left.png')
    img.crop((w // 2, 0, w, h)).save(f'_ocr_fy2025/{base}_b_right.png')
PYEOF
: > _fy2025_scanned_ocr.txt
for leaf in 122 123 124 125 126 127 128 129 130; do
  for half in a_left b_right; do
    f="_ocr_fy2025/page-${leaf}_${half}.png"
    [ -f "$f" ] && tesseract "$f" - --psm 4 2>/dev/null >> _fy2025_scanned_ocr.txt
    echo "" >> _fy2025_scanned_ocr.txt
  done
done

echo "== FY2025: append the real-text Annexure I (pages 234-237) =="
# The FY2025 working-capital figure is NOT restated in this year's own
# Emphasis of Matter section (confirmed by direct visual inspection --
# item 1 there is "Land without Ownership Documents", not going concern).
# It exists only in Annexure I's prior-year-recommendations table, which
# is real (non-scanned) text -- kplc_extract.py's third working-capital
# regex specifically targets this. Concatenating it onto the scanned
# section's OCR output is what makes it reachable by extract_all().
pdftotext -layout -f 234 -l 237 "$FY2025_PDF" _fy2025_annexure1.txt
cat _fy2025_scanned_ocr.txt _fy2025_annexure1.txt > fy2025_oag_ocr.txt

rm -rf _ocr_fy2024 _ocr_fy2025 _fy2025_scanned_ocr.txt _fy2025_annexure1.txt

echo ""
echo "Done. Generated: fy2022_oag.txt fy2023_oag.txt fy2024_oag_ocr.txt fy2025_oag_ocr.txt fy2024_annual_report.txt fy2025_annual_report.txt"
echo "Note: OCR output is not byte-for-byte deterministic across tesseract/poppler versions."
echo "Re-running kplc_validate.py after regenerating these should still land at 18/19 (95%) with the fixed regexes,"
echo "but do not expect the OCR text itself to diff cleanly against a previous run."
