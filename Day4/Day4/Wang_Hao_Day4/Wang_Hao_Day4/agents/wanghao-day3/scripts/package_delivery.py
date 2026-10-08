"""Build an owner-only ZIP with SHA-256 manifest and credential-value scan."""
import argparse
import hashlib
import os
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.venv','node_modules','.pytest_cache','__pycache__','.git'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and not (set(p.relative_to(ROOT).parts)&EXCLUDE)
                 and p.suffix not in {'.pyc','.zip'} and p.name!='MANIFEST.sha256')
    secret=os.environ.get('OPENAI_API_KEY','').encode()
    for file in files:
        content=file.read_bytes()
        if secret and secret in content: raise RuntimeError('A runtime credential value appeared in the package')
    manifest=ROOT/'MANIFEST.sha256'
    manifest.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}\n' for p in files),encoding='utf-8')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(args.output,'w',ZIP_DEFLATED,compresslevel=9) as archive:
        for file in files+[manifest]: archive.write(file,'wanghao-day3/'+file.relative_to(ROOT).as_posix())
    with ZipFile(args.output) as archive:
        assert archive.testzip() is None
        names=archive.namelist()
        assert not any('/'+folder+'/' in name for folder in EXCLUDE for name in names)
        assert not any(name.startswith('wanghao-day3/'+prefix) for name in names for prefix in ['app/','components/','lib/','public/','out/','simulation_day1/'])
    print(args.output.resolve())
    print(f'ZIP integrity OK; {len(names)} files; {args.output.stat().st_size} bytes.')
    print('ZIP SHA-256:',hashlib.sha256(args.output.read_bytes()).hexdigest())

if __name__=='__main__': main()
