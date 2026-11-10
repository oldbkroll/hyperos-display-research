"""Resume at partition boundaries; verify complete image hashes before reuse.

payload-dumper-go reads payload.bin directly from a local ZIP. Never pass
-no-verify or -no-fec. Temporary output is renamed only after SHA256 matches.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from rom_inventory import sha256


parser = argparse.ArgumentParser()
parser.add_argument('rom', type=Path)
parser.add_argument('--partitions', default='system,system_ext,product,mi_ext,vendor,odm,mi_product')
parser.add_argument('--tool', type=Path, default=Path('tools/bin/payload-dumper-go/payload-dumper-go.exe'))
args = parser.parse_args()
inventory = json.loads(Path('analysis/evidence/rom-inventory.json').read_text(encoding='utf-8'))
if args.rom.stat().st_size != inventory['rom']['size'] or sha256(args.rom) != inventory['rom']['sha256']:
    raise SystemExit('ROM identity mismatch; rerun inventory deliberately')
known = {part['name']: part for part in inventory['payload']['partitions']}
output = Path('extracted/images')
output.mkdir(parents=True, exist_ok=True)
for name in args.partitions.split(','):
    if name not in known:
        raise SystemExit(f'Unknown partition: {name}')
    info = known[name]
    target = output / f'{name}.img'
    if target.exists():
        if target.stat().st_size == info['size'] and sha256(target) == info['sha256']:
            print(f'{name}: verified, skipping', flush=True)
            continue
        raise SystemExit(f'{target}: existing image mismatches; investigate without overwriting')
    stage = output / f'{name}.partial'
    stage.mkdir(exist_ok=True)
    command = [str(args.tool.resolve()), '-c', '4', '-p', name, '-o', str(stage.resolve()), str(args.rom.resolve())]
    print('Running:', command, flush=True)
    log = Path(f'analysis/local/extract-{name}.log')
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
    candidate = stage / f'{name}.img'
    if candidate.stat().st_size != info['size'] or sha256(candidate) != info['sha256']:
        raise SystemExit(f'{name}: SHA256/size mismatch')
    candidate.rename(target)
    os.chmod(target, 0o444)
    stage.rmdir()
    print(f'{name}: extracted and verified', flush=True)
