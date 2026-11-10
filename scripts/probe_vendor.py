"""Run in WSL: bounded strings/symbol reconnaissance, not behavior proof.

Only offsets, hashes, property/symbol identifiers are published. All messages
and symbol tables stay in analysis/local. No disassembly is uploaded.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

state = json.loads(Path('extracted/native-files.json').read_text())
targets = {
    'vendor': ['bin/hw/vendor.qti.hardware.display.composer-service', 'lib64/libsdmcore.so',
               'lib64/libsdmutils.so', 'lib64/libsdmclient.so', 'lib64/libsdedrm.so',
               'lib64/libdrmutils.so', 'lib64/libdisplaydebug.so', 'lib64/libsdmextension.so'],
    'system': ['system/bin/surfaceflinger', 'system/lib64/libsurfaceflinger.so'],
    'system_ext': ['lib64/libsurfaceflinger.so', 'lib64/libmisurfaceflinger.so'],
}
pattern = re.compile(r'pluggable|external|hdmi|edid|displayport|bestconfig|max.*fps|fps.*max|config.*mode|mode.*config', re.I)
out = Path('analysis/local/vendor-probe')
out.mkdir(parents=True, exist_ok=True)
results = []
for partition, paths in targets.items():
    for relative in paths:
        source = Path(state[partition]['native_path']) / relative
        if not source.exists():
            continue
        data = source.read_bytes()
        strings = [{'offset': m.start(), 'text': m.group().decode('ascii')} for m in re.finditer(rb'[\x20-\x7e]{5,}', data) if pattern.search(m.group().decode('ascii'))]
        name = source.name
        (out / f'{name}.strings.json').write_text(json.dumps(strings, indent=2) + '\n')
        symbols = subprocess.run(['readelf', '--dyn-syms', '--wide', str(source)], capture_output=True, text=True, check=True).stdout
        symbols = subprocess.run(['c++filt'], input=symbols, capture_output=True, text=True, check=True).stdout
        (out / f'{name}.symbols.txt').write_text(symbols)
        properties = [item for item in strings if re.fullmatch(r'(?:persist\.)?(?:vendor|debug|ro)\.[\w.]+', item['text'])]
        matches = [line.strip() for line in symbols.splitlines() if pattern.search(line)]
        record = {'path': f'{partition}/{relative}', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'property_identifiers': properties, 'matched_string_count': len(strings),
                  'symbol_match_count': len(matches), 'evidence_scope': 'strings/symbols only; control flow must be checked separately'}
        results.append(record)
        print(record['path'], 'strings', len(strings), 'symbols', len(matches))
        for prop in properties:
            print(' ', prop['offset'], prop['text'])
Path('analysis/evidence/vendor-binaries.json').write_text(json.dumps(results, indent=2) + '\n')
