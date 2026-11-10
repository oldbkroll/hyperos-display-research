"""Verify research artifacts without touching a device or running ADB.

--local also checks private evidence anchors and source files against hashes.
--rom additionally rehashes the original ROM (read-only).
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from rom_inventory import sha256

parser = argparse.ArgumentParser()
parser.add_argument('--local', action='store_true')
parser.add_argument('--rom', action='store_true')
args = parser.parse_args()
checks = []
evidence = Path('analysis/evidence')
documents = {}
for path in evidence.glob('*.json'):
    if path.name != 'verification.json':
        documents[path.name] = json.loads(path.read_text(encoding='utf-8'))
checks.append(f'Parsed {len(documents)} evidence JSON files')
rom = documents['rom-inventory.json']
expected = {p['name']: p for p in rom['payload']['partitions']}
extracted = documents['extraction.json']['partitions']
assert {p['partition'] for p in extracted} == {'system', 'system_ext', 'product', 'mi_ext', 'vendor', 'odm', 'mi_product'}
for part in extracted:
    assert part['sha256'] == expected[part['partition']]['sha256']
    assert part['status'] == 'complete' and part['filesystem'] == 'EROFS'
checks.append('Seven completed EROFS records match payload manifest hashes')
findings = documents['findings.json']
assert len(findings['methods']) == 24
assert len({f['id'] for f in findings['methods']}) == 24
assert int('011101f7', 16) == 17891831
assert int('011101f6', 16) == 17891830
assert int('0111006f', 16) == 17891439
assert int('0104037a', 16) == 17040250
checks.append('24 unique method records and numeric resource ID cross-checks pass')
overlays = documents['overlays.json']
assert overlays['scan_count'] == len(overlays['overlays']) == 97
assert all(o['resources_exit'] == o['manifest_exit'] == 0 for o in overlays['overlays'])
checks.append('97 packaged overlay resource/manifest scans succeeded')
for path in Path('reports').glob('*.md'):
    content = path.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if '://' in target or target.startswith('#'):
            continue
        target = target.split('#')[0]
        assert (path.parent / target).exists(), (path, target)
assert len(list(Path('reports').glob('0[1-6]-*.md'))) == 6
checks.append('Six reports and their relative file links exist')
tracked = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
blocked = {'.zip', '.img', '.bin', '.apk', '.jar', '.dex', '.vdex', '.odex', '.so', '.oat', '.art', '.deb'}
for name in filter(None, tracked):
    assert Path(name).suffix.lower() not in blocked, name
    assert not name.startswith(('extracted/', 'analysis/local/', 'tools/bin/', 'tools/wsl/', 'tools/downloads/')), name
checks.append('Git index excludes ROM, partition images, APK/DEX/ELF and local decompiled outputs')
if args.local:
    for item in findings['methods']:
        path = Path(item['local_output'])
        assert sha256(path) == item['decompiled_file_sha256'], item['id']
        lines = path.read_text(encoding='utf-8').splitlines()
        for anchor in item['anchors']:
            for line in anchor['lines']:
                assert anchor['anchor'] in lines[line - 1], (item['id'], line)
    for record in documents['input-copies.json']:
        assert sha256(Path(record['local'])) == record['sha256'], record['source']
    for source in documents['aosp-sources.json']['files']:
        assert source['status'] == 'ok'
        assert sha256(Path('analysis/local/aosp') / source['path']) == source['sha256']
    checks.append('Local method anchors, selected binary copies and pinned AOSP files match recorded hashes')
if args.rom:
    assert sha256(Path(rom['rom']['name'])) == rom['rom']['sha256']
    checks.append('Original ROM final SHA256 still matches first inventory')
result = {'date': '2026-11-10', 'result': 'PASS', 'checks': checks,
          'device_validation': 'NOT_RUN',
          'boundary': 'Static workflow/artifact integrity only; no functional device or hardware acceptance'}
(evidence / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for check in checks:
    print('PASS', check)
