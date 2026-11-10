"""Index defined DEX class names without decompiling; local index, public hashes.

This distinguishes class definitions from mere referenced strings. It does not
prove any method executes or any capability is enabled at runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile
from rom_inventory import varint, sha256


def classes(data):
    if not data.startswith(b'dex\n'):
        raise ValueError('not a standard DEX')
    strings_n, strings_off, types_n, types_off = struct.unpack_from('<4I', data, 56)
    class_n, class_off = struct.unpack_from('<2I', data, 96)
    strings = []
    for i in range(strings_n):
        offset, = struct.unpack_from('<I', data, strings_off + 4 * i)
        _, offset = varint(data, offset)
        end = data.index(0, offset)
        strings.append(data[offset:end].decode('utf-8', errors='replace'))
    types = [strings[struct.unpack_from('<I', data, types_off + 4 * i)[0]] for i in range(types_n)]
    return [types[struct.unpack_from('<I', data, class_off + 32 * i)[0]] for i in range(class_n)]


parser = argparse.ArgumentParser()
parser.add_argument('inputs', nargs='+', type=Path)
args = parser.parse_args()
results = []
for path in args.inputs:
    result = {'path': path.as_posix(), 'size': path.stat().st_size, 'sha256': sha256(path), 'dex': []}
    definitions = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith('classes') and name.endswith('.dex'):
                data = archive.read(name)
                names = classes(data)
                result['dex'].append({'entry': name, 'sha256': hashlib.sha256(data).hexdigest(), 'class_count': len(names)})
                definitions.extend(names)
    local = Path('analysis/local/catalog') / (path.stem + '-classes.txt')
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text('\n'.join(sorted(definitions)) + '\n', encoding='utf-8')
    result['defined_class_count'] = len(definitions)
    results.append(result)
    print(path.name, len(definitions), 'defined classes')
output = Path('analysis/evidence/components.json')
old = json.loads(output.read_text(encoding='utf-8')) if output.exists() else []
by_path = {item['path']: item for item in old + results}
output.write_text(json.dumps(list(by_path.values()), indent=2) + '\n', encoding='utf-8')
