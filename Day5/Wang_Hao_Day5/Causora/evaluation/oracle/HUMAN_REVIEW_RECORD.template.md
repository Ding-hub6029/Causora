# Day 5 Oracle Human Review Record — Template

**Status:** TEMPLATE ONLY. This file is not a human review record and does not authorize, approve, or certify any output.

Complete this record after an actual independent person has checked the frozen expected labels and inputs. Do not use an AI-generated name, a model account, a copied historical statement, or a generic team signature.

| Field | Required entry |
| --- | --- |
| Reviewer name or approved pseudonymous identifier | |
| Role and independence from oracle implementation | |
| Review date/time and timezone | |
| Package SHA-256 | |
| `frozen_control_cases.json` SHA-256 | |
| `shared_control_inputs.json` SHA-256 | |
| `expected_labels.json` SHA-256 | |
| Cases independently checked | List all six IDs or identify omissions |
| Arithmetic/reference used | Manual calculation, spreadsheet, or independent calculator; include version/file hash if retained |
| Result per case | Match / discrepancy, with the checked values |
| Discrepancies and corrections | None or detailed record |
| Reviewer attestation | “I independently reviewed the stated control inputs and expected labels on the date above.” |

## Required follow-up

1. Store the completed record as `evaluation/oracle/HUMAN_REVIEW_RECORD.md`.
2. Update the `source` fields in the frozen controls and benchmark labels from `PENDING_HUMAN_REVIEW...` only after the actual reviewer attests.
3. Re-run the oracle and the benchmark scorer; retain the resulting file hashes.
4. Do not interpret this small-control review as independent reproduction of the 104-week Monte Carlo engine.
