"""Check supplied Day3 backend core/contract bytes without touching them."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-root',type=Path,required=True)
    args=parser.parse_args()
    pins=json.loads((ROOT/'reference/jinzhu_day3/source_pins.json').read_text(encoding='utf-8'))
    for relative,expected in pins['backendFilesSha256'].items():
        actual=hashlib.sha256((args.backend_root/relative).read_bytes()).hexdigest()
        if actual!=expected: raise ValueError('Supplied core/contract changed: '+relative)
    print('PASS: latest supplied backend core/contract hashes unchanged.')
    print('Runtime trace artifacts are intentionally separate from immutable core source pins.')

if __name__=='__main__': main()
