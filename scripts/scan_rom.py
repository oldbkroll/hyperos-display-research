"""Run in WSL. Index file paths and bounded config hits locally, never publish code."""
import json
from pathlib import Path
import re

state = json.loads(Path('extracted/native-files.json').read_text())
pattern = re.compile(r'desktop|freeform|secondary.?display|external.?display|hdmi|displayport|surface_flinger|multi.?display|multi.?window|dp_(?:fps|resolution)|max.?refresh', re.I)
inventory = []
hits = []
for partition, record in state.items():
    root = Path(record['native_path'])
    for path in root.rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        relative = f'{partition}/{path.relative_to(root).as_posix()}'
        size = path.stat().st_size
        inventory.append({'path': relative, 'size': size})
        if (path.suffix in ('.xml', '.prop', '.rc', '.conf', '.json', '.cfg') or path.name == 'build.prop') and size < 2_000_000:
            text = path.read_text(errors='replace')
            for number, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    hits.append({'path': relative, 'line': number, 'text': line[:1200]})
out = Path('analysis/local')
(out / 'file-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
(out / 'config-hits.json').write_text(json.dumps(hits, indent=2) + '\n')
print('Completed partitions:', ', '.join(state))
print('Files:', len(inventory), 'Config hits:', len(hits))
for hit in hits:
    if hit['path'].endswith('build.prop') or 'device_features' in hit['path']:
        print(f"{hit['path']}:{hit['line']}: {hit['text']}")
