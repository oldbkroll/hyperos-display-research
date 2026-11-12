"""Check the native desktop research handoff; never access a device."""

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import struct
import subprocess
from zipfile import ZipFile


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


def elf_relocations(data, section):
    blob = data[section[4]:section[4] + section[5]]
    if not blob.startswith(b'APS2'):
        yield from struct.iter_unpack('<QQq', blob)
        return

    def signed_leb128_values():
        value = shift = 0
        for byte in blob[4:]:
            value |= (byte & 0x7f) << shift
            shift += 7
            if byte & 0x80:
                continue
            yield value - (1 << shift) if byte & 0x40 else value
            value = shift = 0

    stream = signed_leb128_values()
    remaining, offset = next(stream), next(stream)
    addend = 0
    while remaining:
        count, flags = next(stream), next(stream)
        assert 0 < count <= remaining and flags & ~15 == 0
        group_offset = next(stream) if flags & 2 else None
        group_info = next(stream) if flags & 1 else None
        group_addend = next(stream) if flags & 8 and flags & 4 else None
        for _ in range(count):
            offset += next(stream) if group_offset is None else group_offset
            info = next(stream) if group_info is None else group_info
            if flags & 8:
                addend += next(stream) if group_addend is None else group_addend
            else:
                addend = 0
            yield offset, info, addend
        remaining -= count


def elf_relr_addresses(data, section):
    base = 0
    for (entry,) in struct.iter_unpack('<Q', data[section[4]:section[4] + section[5]]):
        if entry & 1:
            for bit in range(1, 64):
                if entry & (1 << bit):
                    yield base + 8 * (bit - 1)
            base += 8 * 63
        else:
            yield entry
            base = entry + 8


def verify_native_lifecycle(record, launcher_path):
    roots = json.loads(Path('extracted/native-files.json').read_text(encoding='utf-8'))
    runtime_path = Path(roots[record['runtime_partition']]['windows_path']) / record['runtime_path']
    assert sha256(runtime_path) == record['runtime_sha256']
    runtime = runtime_path.read_bytes()
    launcher = Path(launcher_path).read_bytes()
    runtime_text = elf_sections(runtime)['.text']
    launcher_sections = elf_sections(launcher)
    launcher_text = launcher_sections['.text']
    relative_targets = {address: addend for address, info, addend in
                        elf_relocations(launcher, launcher_sections['.rela.dyn']) if info == 1027}
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


def verify_direct_branches(branches, images, layouts):
    for item in branches:
        key = item['image']
        text = layouts[key]['.text']
        pc = int(item['pc'], 16)
        assert text[3] <= pc <= text[3] + text[5] - 4, item
        word = struct.unpack_from('<I', images[key], text[4] + pc - text[3])[0]
        assert word >> 26 in (5, 37), item
        displacement = ((word & 0x3ffffff) ^ 0x2000000) - 0x2000000
        assert pc + 4 * displacement == int(item['target'], 16), item


def verify_data_anchors(image, anchors):
    for offset, text in anchors.items():
        start = int(offset, 16)
        value = text.encode('ascii')
        assert image[start:start + len(value)] == value, offset


def verify_minidebug(image, sections, record):
    section = sections['.gnu_debugdata']
    debug = lzma.decompress(image[section[4]:section[4] + section[5]])
    assert hashlib.sha256(debug).hexdigest() == record['sha256']
    debug_sections = elf_sections(debug)
    symtab, strtab = (debug_sections[name] for name in ('.symtab', '.strtab'))
    symbols = {}
    for name, _, _, _, value, _ in struct.iter_unpack('<IBBHQQ', debug[symtab[4]:symtab[4] + symtab[5]]):
        offset = strtab[4] + name
        symbols.setdefault(value, []).append(debug[offset:debug.index(0, offset)].decode())
    for address, fragments in record['symbols'].items():
        assert any(all(part in name for part in fragments) for name in symbols[int(address, 16)]), address


def verify_native_elf_anchors(record, launcher_path):
    roots = json.loads(Path('extracted/native-files.json').read_text(encoding='utf-8'))
    paths = {'launcher': Path(launcher_path)}
    for key, item in record['rom_libraries'].items():
        path = Path(roots[item['partition']]['windows_path']) / item['path']
        assert sha256(path) == item['sha256'], key
        paths[key] = path
    images = {key: path.read_bytes() for key, path in paths.items()}
    layouts = {key: elf_sections(image) for key, image in images.items()}
    relocations = {
        key: {address: (info, addend) for address, info, addend in
              elf_relocations(image, layouts[key]['.rela.dyn'])}
        for key, image in images.items()
    }
    for image, slots in record.get('relative_relocations', {}).items():
        for slot, target in slots.items():
            assert relocations[image][int(slot, 16)] == (1027, int(target, 16)), (image, slot)
    for image, slots in record.get('relr_relocations', {}).items():
        data, sections = images[image], layouts[image]
        addresses = set(elf_relr_addresses(data, sections['.relr.dyn']))
        for slot, target in slots.items():
            address = int(slot, 16)
            assert address in addresses, (image, slot)
            section = next(sh for sh in sections.values() if sh[2] & 2 and sh[1] != 8
                           and sh[3] <= address <= sh[3] + sh[5] - 8)
            offset = section[4] + address - section[3]
            assert struct.unpack_from('<Q', data, offset)[0] == int(target, 16), (image, slot)
    verify_direct_branches(record['direct_branches'], images, layouts)
    for key, anchors in record.get('data_anchors', {}).items():
        verify_data_anchors(images[key], anchors)
    for key, debug in record.get('mini_debug', {}).items():
        verify_minidebug(images[key], layouts[key], debug)
    for item in record['symbol_relocations']:
        key = item['image']
        data, sections = images[key], layouts[key]
        dynsym, dynstr = (sections[name][4] for name in ('.dynsym', '.dynstr'))
        info, addend = relocations[key][int(item['slot'], 16)]
        assert info & 0xffffffff == item.get('type', 257) and addend == 0, item
        symbol = dynsym + 24 * (info >> 32)
        name_offset = dynstr + struct.unpack_from('<I', data, symbol)[0]
        name = data[name_offset:data.index(0, name_offset)].decode()
        assert all(part in name for part in item['symbol_parts']), item
        assert struct.unpack_from('<Q', data, symbol + 8)[0] == int(item['symbol_va'], 16), item


def verify_secondary_aot(record, launcher_path, apk_path):
    dart = record['dart']
    with ZipFile(apk_path) as apk:
        image = apk.read(dart['member'])
    assert hashlib.sha256(image).hexdigest() == dart['sha256']
    sections = elf_sections(image)
    verify_minidebug(image, sections, dart['mini_debug'])
    verify_direct_branches(dart['direct_branches'], {'dart': image}, {'dart': sections})
    verify_data_anchors(image, dart['data_anchors'])
    verify_native_elf_anchors(record['bridge'], launcher_path)
    print('PASS: MiuiHome AOT member, mini debug symbols and native window bridge anchors')


def verify_d10(capture):
    root = Path('analysis/local/device-validation') / capture['directory']
    for name, entry in capture['files'].items():
        source = root / name
        assert sha256(source) == entry['sha256'], source
        if 'lines' in entry:
            lines = source.read_bytes().split(b'\n')
            for line, fragment in entry['lines'].items():
                assert fragment.encode('utf-8') in lines[int(line) - 1], (source, line, fragment)
    print('PASS: archived D10 log, window, compositor and screenshot hashes and line anchors')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='verify private ROM copies and anchors')
    parser.add_argument('--d10', action='store_true', help='verify the archived D10 capture')
    args = parser.parse_args()
    evidence = Path('analysis/evidence')
    data = json.loads((evidence / 'native-desktop-stage2.json').read_text(encoding='utf-8'))
    first_frame = json.loads((evidence / 'native-first-frame.json').read_text(encoding='utf-8'))
    secondary_aot = json.loads((evidence / 'native-secondary-aot.json').read_text(encoding='utf-8'))
    assert first_frame['new_device_validation'] == 'NOT_RUN'
    assert secondary_aot['new_device_validation'] == 'NOT_RUN'
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
        launcher_path = data['inputs'][native['input']]['local']
        verify_native_elf_anchors(data['native_display_routing'], launcher_path)
        print('PASS: native display routing input hashes, direct branches and named relocations')
        verify_native_elf_anchors(first_frame, launcher_path)
        print('PASS: first-frame ROM input hashes, direct branches and relocations')
        verify_secondary_aot(secondary_aot, launcher_path, data['inputs'][secondary_aot['apk_input']]['local'])
    if args.d10:
        verify_d10(first_frame['capture'])
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
