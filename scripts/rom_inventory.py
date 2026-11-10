"""Read-only OTA ZIP/payload manifest inventory; no third-party dependencies.

Field numbers: AOSP system/update_engine/update_metadata.proto.
Unknown protobuf fields are skipped; this is deliberately not a payload writer.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile


def varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        b = data[pos]
        pos += 1
        value |= (b & 127) << shift
        if b < 128:
            return value, pos
    raise ValueError("invalid protobuf varint")


def fields(data):
    out = collections.defaultdict(list)
    pos = 0
    while pos < len(data):
        key, pos = varint(data, pos)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = varint(data, pos)
        elif wire == 2:
            size, pos = varint(data, pos)
            value = data[pos:pos + size]
            if len(value) != size:
                raise ValueError("truncated protobuf")
            pos += size
        elif wire in (1, 5):
            size = 8 if wire == 1 else 4
            value = data[pos:pos + size]
            pos += size
        else:
            raise ValueError(f"unsupported protobuf wire {wire}")
        out[number].append(value)
    return out


def first(msg, key, default=None):
    return msg.get(key, [default])[0]


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(path):
    with zipfile.ZipFile(path) as archive:
        meta_text = archive.read('META-INF/com/android/metadata').decode()
        metadata = dict(line.split('=', 1) for line in meta_text.splitlines() if '=' in line)
        with archive.open('payload.bin') as payload:
            magic, major, size = struct.unpack('>4sQQ', payload.read(20))
            if magic != b'CrAU' or major != 2:
                raise ValueError(f"unsupported payload header: {magic!r} {major}")
            signature_size, = struct.unpack('>I', payload.read(4))
            manifest_bytes = payload.read(size)
            manifest = fields(manifest_bytes)
        parts = []
        for blob in manifest.get(13, []):
            part = fields(blob)
            info = fields(first(part, 7, b''))
            operations = [fields(op) for op in part.get(8, [])]
            parts.append({
                'name': first(part, 1).decode(), 'size': first(info, 1),
                'sha256': first(info, 2, b'').hex(),
                'old_partition_info_present': 6 in part,
                'operations': len(operations),
                'operation_types': dict(collections.Counter(str(first(op, 1)) for op in operations)),
                'payload_data_bytes': sum(first(op, 3, 0) for op in operations),
            })
        dynamic = fields(first(manifest, 15, b''))
        groups = []
        for blob in dynamic.get(1, []):
            group = fields(blob)
            groups.append({'name': first(group, 1).decode(), 'size': first(group, 2),
                           'partitions': [v.decode() for v in group.get(3, [])]})
        return {
            'rom': {'name': path.name, 'size': path.stat().st_size, 'sha256': sha256(path)},
            'disk_free_bytes_at_inventory': shutil.disk_usage(path.parent).free,
            'ota_metadata': metadata,
            'zip_entries': [{'name': i.filename, 'size': i.file_size, 'compressed_size': i.compress_size,
                             'method': i.compress_type} for i in archive.infolist()],
            'payload': {'major': major, 'minor': first(manifest, 12, 0),
                        'block_size': first(manifest, 3, 4096), 'manifest_size': size,
                        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
                        'signature_size': signature_size,
                        'partitions': parts, 'dynamic_groups': groups,
                        'snapshot_enabled': bool(first(dynamic, 2, 0)),
                        'vabc_enabled': bool(first(dynamic, 3, 0)),
                        'vabc_compression': first(dynamic, 4, b'').decode()},
            'payload_properties': archive.read('payload_properties.txt').decode(),
            'verification_scope': 'ZIP SHA256 and manifest inventory; OTA signature authenticity not verified',
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('rom', type=Path)
    parser.add_argument('--output', type=Path, default=Path('analysis/evidence/rom-inventory.json'))
    args = parser.parse_args()
    result = inventory(args.rom.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Saved {args.output}: {len(result['payload']['partitions'])} partitions")
