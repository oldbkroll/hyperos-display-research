"""Read-only aapt2 scan of every packaged overlay APK in completed partitions.

Full dumps stay local. Public output contains hashes and bounded relevant
resource blocks; this does not establish runtime enabled state or idmap validity.
"""
import concurrent.futures
import json
from pathlib import Path
import re
import subprocess
from rom_inventory import sha256

aapt = Path.home() / 'AppData/Local/Android/Sdk/build-tools/37.0.0/aapt2.exe'
state = json.loads(Path('extracted/native-files.json').read_text())
inventory = json.loads(Path('analysis/local/file-inventory.json').read_text())
targets = [item['path'] for item in inventory if '/overlay/' in item['path'] and item['path'].endswith('.apk')]
pattern = re.compile(r'config_.*(?:[Dd]esktop|[Ff]reeform|[Mm]ultiDisplay|[Ss]ystemDecorsOnSecondary|[Ss]econdaryHome|[Ll]auncherForSecondary)|config_supportsMultiWindow')

def inspect(relative):
    partition, rest = relative.split('/', 1)
    source = Path(state[partition]['windows_path']) / rest
    local = Path('analysis/local/overlays') / relative.replace('/', '__')
    local.parent.mkdir(parents=True, exist_ok=True)
    resource = subprocess.run([str(aapt), 'dump', 'resources', str(source)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    manifest = subprocess.run([str(aapt), 'dump', 'xmltree', str(source), '--file', 'AndroidManifest.xml'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    local.with_suffix('.resources.txt').write_text(resource.stdout + resource.stderr, encoding='utf-8')
    local.with_suffix('.manifest.txt').write_text(manifest.stdout + manifest.stderr, encoding='utf-8')
    blocks = re.split(r'(?=^\s{4}resource )', resource.stdout, flags=re.M)
    matches = [block.strip() for block in blocks if pattern.search(block.splitlines()[0] if block else '')]
    attrs = [line.strip() for line in manifest.stdout.splitlines() if any(key in line for key in ('targetPackage', 'isStatic', 'resourcesMap', 'android:priority', 'requiredSystemProperty'))]
    return {'path': relative, 'sha256': sha256(source), 'resources_exit': resource.returncode,
            'manifest_exit': manifest.returncode, 'overlay_attributes': attrs, 'relevant_resources': matches}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(inspect, targets))
Path('analysis/evidence/overlays.json').write_text(json.dumps({
    'scan_count': len(results), 'runtime_state': 'not measured', 'overlays': results,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for item in results:
    if item['relevant_resources']:
        print(item['path'], '\n' + '\n'.join(item['relevant_resources']))
print('Scanned', len(results), 'failures', sum(r['resources_exit'] != 0 or r['manifest_exit'] != 0 for r in results))
