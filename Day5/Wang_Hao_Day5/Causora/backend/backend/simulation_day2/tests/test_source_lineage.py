"""Regression for P2: raw source hashes do not authenticate derived weekly data."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from simulation_day1.build_day1_schemas import build_manifest
from simulation_day2.api_boundary import simulate_v1_boundary
from simulation_day2.deterministic import FROZEN_INTERMEDIATE_SHA256, read_source_manifest, run_unreviewed_preview

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path("simulation_day1/demo_inputs_v1.json")
ORIGINAL = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
REQUEST = json.loads((ROOT / "simulation_day1/examples/simulate_request.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "simulation_day2/examples/UNAPPROVED_TEST_POLICY.json").read_text(encoding="utf-8"))


def make_isolated_snapshot(folder: str, altered: dict) -> Path:
    root = Path(folder)
    for name in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions"):
        source = Path(ORIGINAL[name]["sourceFile"])
        (root / source).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, root / source)
    for source in (MANIFEST_PATH, Path("demo_data/causora_day1_mock.json")):
        (root / source).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, root / source)
    (root / MANIFEST_PATH).write_text(json.dumps(altered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return root


class SourceLineageTests(unittest.TestCase):
    def test_authoritative_day1_digest_and_raw_reconstruction(self):
        raw = (ROOT / MANIFEST_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), FROZEN_INTERMEDIATE_SHA256)
        self.assertEqual(build_manifest(), ORIGINAL)  # all fields rebuilt from frozen originals
        self.assertEqual([row["unitsDemanded"] for row in ORIGINAL["historicalDemand"]["observations"][:2]], [250, 279])
        self.assertEqual(read_source_manifest(ROOT), ORIGINAL)

    def test_swapped_first_two_weeks_same_hashes_total_and_version_are_rejected(self):
        altered = copy.deepcopy(ORIGINAL)
        observations = altered["historicalDemand"]["observations"]
        observations[0]["unitsDemanded"], observations[1]["unitsDemanded"] = (
            observations[1]["unitsDemanded"], observations[0]["unitsDemanded"])
        self.assertEqual([row["unitsDemanded"] for row in observations[:2]], [279, 250])
        self.assertEqual(altered["historicalDemand"]["totalUnits"], ORIGINAL["historicalDemand"]["totalUnits"])
        self.assertEqual(altered["dataVersion"], ORIGINAL["dataVersion"])
        for name in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions"):
            self.assertEqual(altered[name]["sourceSha256"], ORIGINAL[name]["sourceSha256"])
        with tempfile.TemporaryDirectory() as folder:
            root = make_isolated_snapshot(folder, altered)
            with self.assertRaisesRegex(ValueError, "intermediate manifest changed"):
                read_source_manifest(root)
            with self.assertRaisesRegex(ValueError, "intermediate manifest changed"):
                run_unreviewed_preview(REQUEST, POLICY, project_root=root)
            status, response = simulate_v1_boundary(REQUEST, request_id="req-swapped-weeks", project_root=root)
            self.assertEqual((status, response["error"]["code"], response["error"]["details"]["reason"]),
                             (503, "simulation_failed", "dataset_unavailable"))
            # Even if an implementation accidentally accepts the modified digest,
            # an independent CSV reparse still rejects the swapped weekly series.
            digest = hashlib.sha256((root / MANIFEST_PATH).read_bytes()).hexdigest()
            with patch("simulation_day2.deterministic.FROZEN_INTERMEDIATE_SHA256", digest):
                with self.assertRaisesRegex(ValueError, "historical demand observations differ"):
                    read_source_manifest(root)

    def test_complete_manifest_digest_also_binds_other_intermediate_sections(self):
        for name, changed in (
            ("supplierDelivery", {"basePriceUsd": 999.0}),
            ("openingInventory", {"unitsOnHand": 1841}),
            ("noticeRegister", {"event": "changed_synthetic_event"}),
            ("contractAssumptions", {"forecastSource": "altered_provenance"}),
        ):
            with self.subTest(section=name), tempfile.TemporaryDirectory() as folder:
                altered = copy.deepcopy(ORIGINAL)
                if name == "supplierDelivery":
                    altered[name]["orders"][0].update(changed)
                elif name == "noticeRegister":
                    altered[name]["entries"][0].update(changed)
                else:
                    altered[name].update(changed)
                root = make_isolated_snapshot(folder, altered)
                with self.assertRaisesRegex(ValueError, "intermediate manifest changed"):
                    read_source_manifest(root)


if __name__ == "__main__":
    unittest.main()
