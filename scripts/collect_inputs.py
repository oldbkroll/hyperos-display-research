"""Copy a small, explicit set from completed native extraction for Windows tools."""
import json
from pathlib import Path
import shutil
from rom_inventory import sha256

TARGETS = {
    'system_ext': ['framework/miui-services.jar', 'framework/Miui-WindowManager-Shell.jar',
                   'framework/miui-framework.jar', 'framework/xiaomi-framework.jar',
                   'framework/hyperos.rustruntime.jar',
                   'priv-app/MiuiSystemUI/MiuiSystemUI.apk'],
    'product': ['priv-app/MiuiHome/MiuiHome.apk', 'priv-app/MIUIHome/MIUIHome.apk'],
}
state = json.loads(Path('extracted/native-files.json').read_text())
records_path = Path('analysis/evidence/input-copies.json')
records = json.loads(records_path.read_text()) if records_path.exists() else []
by_source = {item['source']: item for item in records}
for partition, targets in TARGETS.items():
    if partition not in state:
        continue
    root = Path(state[partition]['windows_path'])
    for relative in targets:
        source = root / relative
        if not source.exists():
            continue
        target = Path('analysis/local/inputs') / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = sha256(source)
        if not target.exists() or sha256(target) != digest:
            shutil.copyfile(source, target)
        by_source[f'{partition}/{relative}'] = {
            'source': f'{partition}/{relative}', 'local': target.as_posix(),
            'sha256': digest, 'size': target.stat().st_size}
        print(partition, relative, target.stat().st_size)
records_path.write_text(json.dumps(list(by_source.values()), indent=2) + '\n', encoding='utf-8')
