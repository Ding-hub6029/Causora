"""Load the supplied human review only; policy and trace release stay gated."""
import argparse, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535: parser.error("port must be 1..65535")
    os.environ.pop("CAUSORA_DEV_UNREVIEWED_MODE", None)
    os.environ["CAUSORA_REVIEW_BUNDLE_DIR"] = str(ROOT / "reviewed/wang-2026-10-07")
    os.environ["CAUSORA_REVIEW_VERIFIER"] = "app.release_verifiers:verify_reviewed_bundle_record"
    import uvicorn
    uvicorn.run("app.service:app", host="127.0.0.1", port=args.port)
if __name__ == "__main__": main()
