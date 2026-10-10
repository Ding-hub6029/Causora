"""CLI for Day5 fair evaluation artifacts.  It has no provider or network code."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import (
    build_dispatch_bundle, create_freeze, import_external_actual_capture,
    pending_metrics, score_sealed_actual_capture, seal_predictions, verify_freeze,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline-only Day5 fair evaluation artifact manager")
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="hash and freeze inputs, labels, prompt, config, scorer, and source identity")
    for name in ("inputs", "labels", "prompt", "model-config", "scoring-source", "source-corpus", "evidence-registry", "output"):
        freeze.add_argument(f"--{name}", type=Path, required=True)
    freeze.add_argument("--author", required=True)
    freeze.add_argument("--authorization-status", default="NO_NEW_PROVIDER_AUTHORIZATION")
    dispatch = sub.add_parser("dispatch", help="write input-only model dispatch bundle")
    dispatch.add_argument("--freeze", type=Path, required=True); dispatch.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify-freeze", help="fail if any frozen artifact changed")
    verify.add_argument("--freeze", type=Path, required=True)
    imported = sub.add_parser("import-actual", help="import an externally executed actual capture; rejects fixtures")
    imported.add_argument("--freeze", type=Path, required=True); imported.add_argument("--capture", type=Path, required=True); imported.add_argument("--output", type=Path, required=True)
    seal = sub.add_parser("seal", help="seal imported output hash before scoring")
    seal.add_argument("--freeze", type=Path, required=True); seal.add_argument("--predictions", type=Path, required=True); seal.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score", help="score a sealed actual capture")
    score.add_argument("--freeze", type=Path, required=True); score.add_argument("--predictions", type=Path, required=True); score.add_argument("--seal", type=Path, required=True); score.add_argument("--output", type=Path, required=True)
    pending = sub.add_parser("pending-metrics", help="write truthful N/A metrics without a model call")
    pending.add_argument("--output", type=Path, required=True); pending.add_argument("--reason", default=None)
    args = parser.parse_args()
    if args.command == "freeze":
        result = create_freeze(inputs_path=args.inputs, labels_path=args.labels, prompt_path=args.prompt,
            model_config_path=args.model_config, scoring_source_path=args.scoring_source,
            source_corpus_path=args.source_corpus, evidence_registry_path=args.evidence_registry,
            output_path=args.output, author=args.author,
            authorization_status=args.authorization_status)
    elif args.command == "dispatch": result = build_dispatch_bundle(freeze_path=args.freeze, output_path=args.output)
    elif args.command == "verify-freeze": result = verify_freeze(args.freeze)
    elif args.command == "import-actual": result = import_external_actual_capture(freeze_path=args.freeze, raw_capture_path=args.capture, output_path=args.output)
    elif args.command == "seal": result = seal_predictions(freeze_path=args.freeze, predictions_path=args.predictions, output_path=args.output)
    elif args.command == "score": result = score_sealed_actual_capture(freeze_path=args.freeze, predictions_path=args.predictions, seal_path=args.seal, output_path=args.output)
    else:
        if args.output.exists():
            raise FileExistsError(f"Refusing to overwrite evaluation evidence: {args.output}")
        result = pending_metrics(reason=args.reason) if args.reason else pending_metrics()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
