"""CLI for controlled synthetic PDF preprocessing and self-attested promotion.

Run from the combined project's `causora/` root; no network service is created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .pipeline import digest, load_json, prepare, promote, review_template


def _write(folder: Path, relative: str, value: dict) -> None:
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _artifact_map(products: dict) -> dict[str, dict]:
    return {"approved_review.json": products["approvedReview"],
            "review_scope.json": products["reviewScope"],
            "reviewed_evidence_summary.json": products["reviewedEvidenceSummary"],
            "dataset_success.json": products["datasetSuccess"],
            "jinzhu_contract_input.json": products["jinzhuContractInput"],
            "review_receipt.json": products["reviewReceipt"],
            **{f"evidence_responses/{key}.json": value
               for key, value in products["evidenceSuccessById"].items()}}


def _publish(directory: Path, artifacts: dict[str, dict], *, manifest_meta: dict | None = None) -> None:
    directory = directory.resolve()
    if directory.exists():
        raise FileExistsError(f"Refusing to overwrite an existing audit directory: {directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".causora-day2-", dir=directory.parent) as staging:
        temp = Path(staging)
        for name, payload in artifacts.items():
            _write(temp, name, payload)
        if manifest_meta is not None:
            hashes = {name: hashlib.sha256((temp / name).read_bytes()).hexdigest()
                      for name in sorted(artifacts)}
            _write(temp, "bundle_manifest.json", {
                "kind": "CAUSORA_SELF_ATTESTED_SYNTHETIC_BUNDLE_V1",
                "scopeSha256": manifest_meta["scopeSha256"],
                "canonicalReviewSha256": manifest_meta["reviewSha256"],
                "dataVersion": manifest_meta["dataVersion"],
                "filesSha256": hashes,
                "warning": "Local hashes detect accidental change but do NOT authenticate a human reviewer or prove real-world facts.",
            })
        # One directory-level operation: no partially written, apparently ready review.
        os.rename(temp, directory)
    print(f"Created {len(artifacts) + int(manifest_meta is not None)} artifact(s) in {directory}")


def verify_bundle(root: Path, bundle: Path) -> None:
    bundle = bundle.resolve()
    meta = load_json(bundle / "bundle_manifest.json")
    if meta["kind"] != "CAUSORA_SELF_ATTESTED_SYNTHETIC_BUNDLE_V1":
        raise ValueError("Unknown local bundle kind")
    hashes = meta["filesSha256"]
    if not isinstance(hashes, dict):
        raise ValueError("Missing file-hash map")
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if actual != set(hashes) | {"bundle_manifest.json"}:
        raise ValueError("Bundle file set changed")
    for name, expected in hashes.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or len(expected) != 64:
            raise ValueError("Unsafe or invalid bundle manifest entry")
        actual_hash = hashlib.sha256((bundle / path).read_bytes()).hexdigest()
        if actual_hash != expected:
            raise ValueError(f"Bundle artifact hash changed: {name}")
    saved_review = load_json(bundle / "approved_review.json")
    expected_products = promote(root, saved_review)  # checks current source/code/DTO and review scope
    if meta["scopeSha256"] != saved_review["scopeSha256"] or meta["canonicalReviewSha256"] != digest(saved_review):
        raise ValueError("Bundle manifest not bound to review scope/decisions")
    if meta["dataVersion"] != expected_products["datasetSuccess"]["dataVersion"]:
        raise ValueError("Bundle dataVersion changed")
    if set(hashes) != set(_artifact_map(expected_products)):
        raise ValueError("Incomplete bundle")
    for name, expected in _artifact_map(expected_products).items():
        if load_json(bundle / name) != expected:
            raise ValueError(f"Bundle {name} differs from a fresh PDF-bound review promotion")
    print("Bundle hashes, exact review, source PDF and cross-owner DTO links verified. "
          "Reviewer identity is NOT authenticated; no simulator has run.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Wang Day 2 synthetic contract -> reviewed DTOs")
    parser.add_argument("action", choices=("preprocess", "promote", "verify"))
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Combined causora/ root")
    parser.add_argument("--out", type=Path, help="NEW directory; never overwritten for preprocess/promote")
    parser.add_argument("--review", type=Path, help="Human-edited review_request.json; only for promote")
    parser.add_argument("--bundle", type=Path, help="Existing reviewed output directory; only for verify")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    if args.action == "verify":
        if args.bundle is None or args.review is not None or args.out is not None:
            parser.error("verify needs --bundle and no --review/--out")
        verify_bundle(root, args.bundle)
    elif args.action == "preprocess":
        if args.review is not None or args.bundle is not None or args.out is None:
            parser.error("preprocess needs --out only")
        summary, baseline, assumptions, hashes = prepare(root)
        template = review_template(summary, baseline, assumptions, hashes)
        _publish(args.out, {"evidence_pending.json": summary.model_dump(mode="json"),
                            "review_request.json": template})
        print(f"Matched {sum(x.quote_matched for x in summary.records)}/{len(summary.records)} synthetic PDF clauses. "
              "NO field is manually verified; NO BusinessVariable, simulation or real approval was published.")
    else:
        if args.review is None or args.bundle is not None or args.out is None:
            parser.error("promote requires --review and --out, not --bundle")
        if args.review.stat().st_size > 1_000_000:
            raise ValueError("Review JSON is too large")
        artifacts = promote(root, load_json(args.review))
        _publish(args.out, _artifact_map(artifacts), manifest_meta={
            "scopeSha256": artifacts["reviewReceipt"]["scopeSha256"],
            "reviewSha256": artifacts["reviewReceipt"]["reviewSha256"],
            "dataVersion": artifacts["datasetSuccess"]["dataVersion"],
        })
        print("SELF-ATTESTED SYNTHETIC review promoted to a typed DatasetSuccess fixture; "
              "review, scope and local file hashes retained. NOT authenticated and NOT simulated.")


if __name__ == "__main__":
    main()
