"""Check the native desktop research handoff; never access a device."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='verify private ROM copies and anchors')
    args = parser.parse_args()
    evidence = Path('analysis/evidence')
    data = json.loads((evidence / 'native-desktop-stage2.json').read_text(encoding='utf-8'))
    pinned = {r['path']: r['sha256'] for r in json.loads((evidence / 'components.json').read_text(encoding='utf-8'))}
    pinned.update({r['local']: r['sha256'] for r in json.loads((evidence / 'input-copies.json').read_text(encoding='utf-8'))})
    methods = data['method_records']
    assert data['device_validation'] == 'NOT_RUN'
    assert len({m['id'] for m in methods}) == len(methods) > 0
    for key, record in data['inputs'].items():
        assert re.fullmatch(r'[0-9a-f]{64}', record['sha256']), key
        if record['local'] in pinned:
            assert record['sha256'] == pinned[record['local']], key
        if args.local:
            assert sha256(record['local']) == record['sha256'], key
    for item in methods:
        assert item['input'] in data['inputs'], item['id']
        assert item['anchors'], item['id']
        if args.local:
            source = Path(item['local_output'])
            assert sha256(source) == item['decompiled_file_sha256'], item['id']
            lines = source.read_text(encoding='utf-8').splitlines()
            for anchor in item['anchors']:
                assert anchor['lines'], (item['id'], anchor['anchor'])
                assert all(anchor['anchor'] in lines[i - 1] for i in anchor['lines']), (item['id'], anchor)
    if args.local:
        native = data['native_anchors']
        with open(data['inputs'][native['input']]['local'], 'rb') as stream:
            for field, anchor in (('class_name_rodata_offset', b'com.miui.home.launcher.SecondaryDisplayLauncher'),
                                  ('ui_name_rodata_offset', b'SecondaryDisplayLauncherUi')):
                stream.seek(int(native[field], 16))
                assert stream.read(len(anchor)) == anchor, field
    documents = [Path('README.md'), Path('analysis/README.md'), *Path('reports').glob('*.md'), *Path('docs').glob('*.md')]
    count = 0
    for source in documents:
        for raw in re.findall(r'\]\(([^)]+)\)', source.read_text(encoding='utf-8')):
            target = raw.split('#', 1)[0]
            if target and '://' not in target:
                assert (source.parent / target).exists(), (source, target)
                count += 1
    blocked = {'.zip', '.img', '.bin', '.apk', '.jar', '.dex', '.vdex', '.odex', '.so', '.oat', '.art', '.deb'}
    tracked = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
    for path in filter(None, tracked):
        assert Path(path).suffix.lower() not in blocked, path
        assert not path.startswith(('extracted/', 'analysis/local/', 'tools/bin/', 'tools/wsl/', 'tools/downloads/')), path
    print(f'PASS: {len(methods)} evidence records, {count} relative links, public Git index')
    if args.local:
        print('PASS: ROM input SHA-256, method hashes and line anchors, two ELF string offsets')
    print('Device validation: NOT_RUN')


if __name__ == '__main__':
    main()
