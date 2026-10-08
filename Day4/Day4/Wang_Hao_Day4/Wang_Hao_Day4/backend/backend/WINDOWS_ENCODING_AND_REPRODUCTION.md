# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Windows Encoding and Data Reproduction

The script writes JSON bytes as UTF-8 without BOM and LF (\n), avoiding Windows text-mode CRLF conversion that would alter SHA-256.

From backend/:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\scripts\reproduce_deng_day3_data.py `
  --out "$env:TEMP\deng-day3-reproduced" `
  --expected-manifest ..\data\deng_day3_data_manifest.json
```

Expected: `REPRODUCTION_PASS: previewId and all three delivered data-file SHA-256 values match.`

Files deng_day3_monte_carlo_full_UNAPPROVED.json, deng_day3_matrix_deltas_UNAPPROVED.json and deng_day3_formula_traces_UNAPPROVED.json must be UTF-8/no BOM/LF and match bytes/SHA in ../data/deng_day3_data_manifest.json. A new generation timestamp affects only the new manifest, not these three computed files. .gitattributes pins source/JSON/Markdown/CSV/TS to LF; Windows .cmd launchers retain CRLF for CMD compatibility.
