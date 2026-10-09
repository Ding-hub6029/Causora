# Wang reviewed-bundle file format

Create a directory and point `CAUSORA_REVIEW_BUNDLE_DIR` at it. It must contain `reviewed_contract.json` and `review_record.json`. Both are required.

## reviewed_contract.json

```json
{
  "kind": "causora.wang.reviewed-contract-bundle.v1",
  "datasetId": "ds-001",
  "dataVersion": "reviewed-contract-data-version",
  "contract": { "<all exact v1 contract fields>": "<reviewed values>" },
  "contractSource": { "sourceFile": "original_contract.pdf", "sourceSha256": "<64 lowercase hex>" },
  "fieldProvenance": {
    "terminationFeeUsd": {
      "evidenceId": "EV-...", "sourceFile": "original_contract.pdf",
      "sourceSha256": "<source file SHA-256>", "reviewItemId": "review-row-..."
    }
  }
}
```

`fieldProvenance` must cover the exact same complete set of contract keys as `contract`, including dates, notices, prices/floors and `evidenceIds`.

## review_record.json

```json
{
  "kind": "causora.wang.review-record.v1",
  "status": "reviewed",
  "reviewId": "immutable-review-record-id",
  "reviewerRole": "contract_reviewer",
  "reviewerId": "wang-hao",
  "recordedAtUtc": "2026-10-07T00:00:00Z",
  "contractPayloadSha256": "<canonical JSON SHA-256 of contract>",
  "fieldProvenanceSha256": "<canonical JSON SHA-256 of fieldProvenance>",
  "reviewedItems": [{ "id": "review-row-01", "status": "reviewed" }]
}
```

At least 11 unique reviewed items are required. `reviewRecordSha256` is automatically calculated from this **record file** and is intentionally never reused as the original contract PDF's `sourceSha256`.
