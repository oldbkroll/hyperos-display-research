"""Check the native desktop research handoff; never access a device."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def elf_sections(data):
    assert data[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', data, 18)[0] == 183
    header_offset = struct.unpack_from('<Q', data, 40)[0]
    entry_size, count, names_index = struct.unpack_from('<HHH', data, 58)
    assert entry_size == 64
    entries = [struct.unpack_from('<IIQQQQIIQQ', data, header_offset + i * entry_size) for i in range(count)]
    names_offset = entries[names_index][4]
    return {data[names_offset + entry[0]:data.index(0, names_offset + entry[0])].decode(): entry
            for entry in entries}


def verify_native_lifecycle(record, launcher_path):
    roots = json.loads(Path('extracted/native-files.json').read_text(encoding='utf-8'))
    runtime_path = Path(roots[record['runtime_partition']]['windows_path']) / record['runtime_path']
    assert sha256(runtime_path) == record['runtime_sha256']
    runtime = runtime_path.read_bytes()
    launcher = Path(launcher_path).read_bytes()
    runtime_text = elf_sections(runtime)['.text']
    launcher_sections = elf_sections(launcher)
    launcher_text = launcher_sections['.text']
    rela = launcher_sections['.rela.dyn']
    relative_targets = {address: addend for address, info, addend in
                        struct.iter_unpack('<QQq', launcher[rela[4]:rela[4] + rela[5]]) if info == 1027}
    for callback in record['callbacks']:
        slot = int(callback['slot'], 16)
        base = int(record[f"{callback['table']}_vtable_va"], 16)
        target = int(callback['launcher_target_va'], 16)
        accessor = int(callback['runtime_accessor_va'], 16)
        instruction = struct.unpack_from('<I', runtime, accessor + 16 - runtime_text[3] + runtime_text[4])[0]
        assert instruction == 0xf9400100 | ((slot // 8) << 10), callback['name']
        assert relative_targets[base + slot] == target, callback['name']
        if callback.get('returns_immediately'):
            assert struct.unpack_from('<I', launcher, target - launcher_text[3] + launcher_text[4])[0] == 0xd65f03c0
    print(f"PASS: {len(record['callbacks'])} named lifecycle slots and launcher relocation targets")


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
        verify_native_lifecycle(data['native_lifecycle'], data['inputs'][native['input']]['local'])
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
