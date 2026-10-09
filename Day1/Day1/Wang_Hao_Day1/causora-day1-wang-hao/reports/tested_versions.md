# Tested Environment (2026-10-05 UTC+08)

| Tool/library | Version tested | Purpose |
| --- | --- | --- |
| Ubuntu | 24.04 (sandbox) | Test host |
| Python | 3.12.3 | Evidence extraction and tests |
| Pydantic | 2.13.5 | Internal schema/provenance |
| PyMuPDF | 1.28.2 | PDF text and locator |
| RapidFuzz | 3.14.6 | Conservative candidate ratio |
| ReportLab | 4.5.1 | Original one-page fixture generation |
| OpenAI Python SDK | 2.54.0 | Configured proxy smoke |
| pytest | 9.1.1 | 50 Python tests, including explicit-UTF-8 regression |
| jsonschema | 4.26.0 | Structural frontend schema tests |
| Node.js | 22.13.0 | v4.1 TypeScript and frontend validation |
| npm | 10.9.2 | Locked frontend dependency installation |
| TypeScript | 5.9.3 | v4.1 runtime validator/transpilation |
| Next.js | 15.5.27 | Baseline and adapted preview production builds |
| Git | 2.43.0 | Available, but no team repo was changed |

`requirements.txt` specifies compatible Python ranges rather than exact frozen transitive versions. Re-run the suite after installing in a new environment. The TS/Next versions came from Xiangfeng's existing lockfile with `npm ci`. They are not dependencies of Wang's Python-only checks. No Node modules or virtual environments are shipped in the ZIP.

**Encoding verification:** This Ubuntu host was tested with both its ordinary UTF-8 default and `LC_ALL=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 PYTHONIOENCODING=utf-8`. Each passed all 50. This emulates the default-decoding failure reported on Windows but **does not claim execution on an actual Windows computer**.
