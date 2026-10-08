"""Check the published file inventory without modifying the package."""
from pathlib import Path
import hashlib
import os

root = Path(__file__).resolve().parents[1]
if os.name == 'nt': root = Path('\\\\?\\' + str(root))
manifest = root / 'MANIFEST.sha256'
failures = []
count = 0
for line in manifest.read_text(encoding='utf-8').splitlines():
    expected, relative = line.split('  ', 1)
    path = (root / relative).resolve()
    count += 1
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        failures.append(relative + ': missing or outside package')
    elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        failures.append(relative + ': changed bytes')
if failures:
    print('\n'.join(failures))
    raise SystemExit(1)
print(f'PASS: {count} published files match their SHA-256 inventory.')
