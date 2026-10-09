"""Verify the complete current delivery inventory without changing files."""
from pathlib import Path, PurePosixPath
import hashlib
import os

root = Path(__file__).resolve().parents[1]
extended_prefix = chr(92) * 2 + '?' + chr(92)
if os.name == 'nt' and not str(root).startswith(extended_prefix):
    root = Path(extended_prefix + str(root))
manifest = root / 'MANIFEST.sha256'
failures = []
listed = set()
for line in manifest.read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    expected, relative = line.split('  ', 1)
    normalized = PurePosixPath(relative)
    if normalized.is_absolute() or '..' in normalized.parts or relative in listed:
        failures.append(relative + ': unsafe or duplicate path')
        continue
    listed.add(relative)
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        failures.append(relative + ': missing or outside package')
    elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        failures.append(relative + ': changed bytes')
ignored = {'node_modules', '.next', '.venv', 'venv', '.git', '__pycache__', '.pytest_cache', '.runtime', 'out', 'builds'}
actual = set()
for current, dirs, names in os.walk(root):
    dirs[:] = [name for name in dirs if name not in ignored]
    for name in names:
        if name == '.env' or name.endswith(('.pyc', '.pyo', '.tsbuildinfo')): continue
        relative = (Path(current) / name).relative_to(root).as_posix()
        if relative != 'MANIFEST.sha256': actual.add(relative)
failures.extend(name + ': not listed in current inventory' for name in sorted(actual - listed))
if failures:
    print('\n'.join(failures))
    raise SystemExit(1)
print(f'PASS: all {len(listed)} published files match the current SHA-256 inventory.')
