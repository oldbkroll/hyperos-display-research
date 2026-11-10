"""WSL user-space EROFS extraction, no mounts or writes to source images.

Only partitions with a verified image are accepted. A .complete marker is
written after fsck exits successfully; reruns skip only matching image hashes.
"""
import argparse
import json
from pathlib import Path
import subprocess
from rom_inventory import sha256

parser = argparse.ArgumentParser()
parser.add_argument('--partitions', default='system,system_ext,product,mi_ext,vendor,odm,mi_product')
args = parser.parse_args()
root = Path.cwd().resolve()
inventory = json.loads((root / 'analysis/evidence/rom-inventory.json').read_text(encoding='utf-8'))
expected = {item['name']: item['sha256'] for item in inventory['payload']['partitions']}
def wslpath(path):
    return subprocess.check_output(['wsl', '-d', 'Ubuntu-24.04', '--', 'wslpath', '-a', path.resolve().as_posix()], text=True).strip()

tool = root / 'tools/wsl/root/usr/bin/fsck.erofs'
results = []
for name in args.partitions.split(','):
    image = root / 'extracted/images' / f'{name}.img'
    if not image.exists():
        raise SystemExit(f'Missing complete image: {image}')
    digest = sha256(image)
    if digest != expected.get(name):
        raise SystemExit(f'{name}: image does not match the payload manifest')
    with image.open('rb') as stream:
        stream.seek(1024)
        magic = stream.read(4).hex()
    if magic != 'e2e1f5e0':
        raise SystemExit(f'{name}: unsupported filesystem magic {magic}')
    output = root / 'extracted/files' / name
    marker = output / '.complete.json'
    if marker.exists() and json.loads(marker.read_text())['image_sha256'] == digest:
        print(f'{name}: complete, skipping', flush=True)
        continue
    output.mkdir(parents=True, exist_ok=True)
    command = ['wsl', '-d', 'Ubuntu-24.04', '--', wslpath(tool),
               '--no-preserve', '--overwrite', f'--extract={wslpath(output)}', wslpath(image)]
    print(f'{name}: EROFS extraction', flush=True)
    with (root / 'analysis/local' / f'fsck-{name}.log').open('w', encoding='utf-8') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
    result = {'partition': name, 'filesystem': 'EROFS', 'image_sha256': digest,
              'command': command, 'status': 'complete'}
    marker.write_text(json.dumps(result, indent=2), encoding='utf-8')
    results.append(result)
    print(f'{name}: complete', flush=True)
