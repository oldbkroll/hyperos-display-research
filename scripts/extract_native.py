"""Run under WSL Python: verified EROFS extraction on its native ext4 filesystem.

No root or mounts; copies only selected source images, verifies before reuse.
Windows can inspect files using the UNC paths saved in extracted/native-files.json.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from rom_inventory import sha256

parser = argparse.ArgumentParser()
parser.add_argument('--partitions', default='system,system_ext,product,mi_ext,vendor,odm,mi_product')
args = parser.parse_args()
workspace = Path.cwd()
inventory = json.loads((workspace / 'analysis/evidence/rom-inventory.json').read_text())
identity = inventory['rom']['sha256'][:16]
native = Path.home() / '.local/share/hyperos-display-research' / identity
native.mkdir(parents=True, exist_ok=True)
known = {item['name']: item for item in inventory['payload']['partitions']}
tool = workspace / 'tools/wsl/root/usr/bin/fsck.erofs'
state_path = workspace / 'extracted/native-files.json'
state = json.loads(state_path.read_text()) if state_path.exists() else {}
for name in args.partitions.split(','):
    info = known[name]
    image = native / 'images' / f'{name}.img'
    image.parent.mkdir(exist_ok=True)
    if not image.exists():
        print(f'{name}: copying verified source to WSL ext4', flush=True)
        partial = image.with_suffix('.partial')
        shutil.copyfile(workspace / 'extracted/images' / f'{name}.img', partial)
        if sha256(partial) != info['sha256']:
            raise SystemExit(f'{name}: copied hash mismatch')
        partial.rename(image)
        image.chmod(0o444)
    elif sha256(image) != info['sha256']:
        raise SystemExit(f'{name}: existing native image mismatch, refusing overwrite')
    with image.open('rb') as stream:
        stream.seek(1024)
        if stream.read(4) != bytes.fromhex('e2e1f5e0'):
            raise SystemExit(f'{name}: not EROFS')
    output = native / 'files' / name
    output.mkdir(parents=True, exist_ok=True)
    marker = output / '.complete.json'
    command = [str(tool), '--no-preserve', '--overwrite', f'--extract={output}', str(image)]
    if not marker.exists():
        print(f'{name}: native EROFS extraction', flush=True)
        with (workspace / f'analysis/local/fsck-native-{name}.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        marker.write_text(json.dumps({'image_sha256': info['sha256'], 'command': command}))
    elif json.loads(marker.read_text())['image_sha256'] != info['sha256']:
        raise SystemExit('Native extraction marker identity mismatch')
    unc = subprocess.check_output(['wslpath', '-w', str(output)], text=True).strip()
    state[name] = {'native_path': str(output), 'windows_path': unc,
                   'sha256': info['sha256'], 'filesystem': 'EROFS', 'status': 'complete'}
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    print(f'{name}: complete ({unc})', flush=True)
