# PesaCheck Prototype — KPLC Reconciliation Engine

Automates the extraction, cross-checking, and disclosure-gap detection
behind [this reconciliation](https://rawlingsmuhinja.substack.com/p/kenya-powers-auditor-flagged-a-kshs)
of Kenya Power's Auditor-General reports against its own shareholder-facing
narrative — four fiscal years, two real-text sources, two OCR'd from
scanned pages embedded in the company's own Integrated Annual Reports.

**Full writeup on building and independently auditing this tool:**
[I Built a Tool to Automate My Own Reconciliation Method. Then I Tried to Break It.](https://rawlingsmuhinja.substack.com/p/i-built-a-tool-to-automate-my-own)

## What it does

1. **Extracts** headline figures (working capital deficit, RES receivables,
   county government receivables, land title issues, KenGen/IPP cost
   disparity) from narrative prose across four Auditor-General reports —
   deliberately sentence-level regex extraction, not table parsing, since
   each finding is stated in prose and phrasing shifts year to year.
2. **Validates** every extracted figure against a hand-verified ground
   truth dataset.
3. **Checks** whether each audited finding also appears, quantified, in
   the company's own shareholder-facing narrative sections — the actual
   question this whole method exists to answer.

## Result

18 of 19 in-scope ground-truth figures match exactly or within an
explained rounding difference (95%), independently reproduced from a
clean directory using only the four source PDFs. Full audit trail,
including six real bugs found and fixed by a cold, independent review,
is in the linked writeup above.

## Files

- `kplc_extract.py` — figure extraction across all 4 fiscal years
- `kplc_validate.py` — validation against the ground-truth dataset
- `kplc_narrative_check.py` — the narrative-absence check
- `build_kplc_sources.sh` — regenerates all intermediate OCR/text files
  deterministically from the four source PDFs (poppler-utils, tesseract-ocr,
  Python 3 + pdfplumber + Pillow required)

## Sources

The four Auditor-General reports for FY2022–FY2025 are public documents,
available from [oagkenya.go.ke](https://www.oagkenya.go.ke) and Kenya
Power's own published Integrated Annual Reports.

## What this is, and isn't

This is a prototype that automates the *extraction and cross-checking*
layer of a reconciliation. It is not a replacement for the judgment call
of whether a flagged match is genuine — during testing, the narrative
checker itself produced one coincidental false-positive match, caught
only by checking context, not by the tool. That limit is disclosed in
full in the writeup linked above, not smoothed over here.
