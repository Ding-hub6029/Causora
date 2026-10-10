"""Verify all packaged files against MANIFEST.sha256 without a shell dependency."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=ROOT/'MANIFEST.sha256'
    if not manifest.is_file(): raise FileNotFoundError('MANIFEST.sha256 is missing')
    count=0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        expected,relative=line.split('  ',1)
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Missing or unsafe manifest path: '+relative)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected: raise ValueError('File integrity mismatch: '+relative)
        count+=1
    print(f'PASS: {count} packaged files match their SHA-256 digests.')

if __name__=='__main__': main()
