"""Assemble the supplied Jinzhu testable + Wang Day2 modules, byte-for-byte.
No frontend/site is included; no review is promoted. New directory only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import shutil
import stat
import tempfile
from zipfile import ZipFile

JINZHU_ALLOWED={'simulation_day1','simulation_day2','lib','demo_data','golden','public','API_CONTRACT.md','JINZHU_TESTABLE_MANIFEST.sha256'}
WANG_ALLOWED={'evidence_day2','causora_day1'}


def assemble(jinzhu_zip:Path,wang_zip:Path,out:Path):
    if out.exists(): raise FileExistsError('Use a new workspace directory; never overlay team sources')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='.causora-dev-') as staging:
        root=Path(staging)/'causora'; root.mkdir()
        inputs={}
        for label,path,allowed in [('jinzhu',jinzhu_zip,JINZHU_ALLOWED),('wang_day2',wang_zip,WANG_ALLOWED)]:
            inputs[label]={'archiveSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'archiveName':path.name}
            with ZipFile(path) as archive:
                for info in archive.infolist():
                    name=PurePosixPath(info.filename)
                    if name.is_absolute() or '..' in name.parts or '\\' in info.filename:
                        raise ValueError('Unsafe archive member')
                    if info.is_dir(): continue
                    if stat.S_ISLNK(info.external_attr>>16): raise ValueError('Symlink not permitted')
                    if not name.parts or name.parts[0]!='causora': continue
                    relative=Path(*name.parts[1:])
                    if not relative.parts or relative.parts[0] not in allowed: continue
                    target=root/relative; data=archive.read(info)
                    if target.exists() and target.read_bytes()!=data: raise ValueError('Conflicting team source: '+str(relative))
                    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        for file in ['simulation_day2/deterministic.py','simulation_day1/demo_inputs_v1.json','evidence_day2/cli.py','causora_day1/claim_checks.py','lib/contracts.ts']:
            if not (root/file).is_file(): raise ValueError('Required module absent: '+file)
        manifest={'kind':'CAUSORA_UNREVIEWED_DEV_WORKSPACE','humanReviewStatus':'pending','decisionReady':False,
                  'inputs':inputs,'filesSha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}}
        (root/'DEV_WORKSPACE.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        shutil.move(str(root),str(out))
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jinzhu-zip',type=Path,required=True); p.add_argument('--wang-day2-zip',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    manifest=assemble(a.jinzhu_zip,a.wang_day2_zip,a.out)
    print(a.out.resolve()); print(f"Copied {len(manifest['filesSha256'])} unchanged dependency files; reviews remain pending.")

if __name__=='__main__': main()
