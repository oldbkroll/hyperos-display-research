"""Install only the two Windows research tools in this project, pin and hash-check."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile

TOOLS = [
    {'name': 'payload-dumper-go', 'version': '2.1.0',
     'url': 'https://github.com/ssut/payload-dumper-go/releases/download/2.1.0/payload-dumper-go_2.1.0_windows_amd64.tar.gz',
     'sha256': '45483c54bdd9219b8dcdb757256e7ce7a2bf9552d0e43f32e03389a1f0c55b15'},
    {'name': 'jadx', 'version': '1.5.6',
     'url': 'https://github.com/skylot/jadx/releases/download/v1.5.6/jadx-1.5.6.zip',
     'sha256': '545ea2be9c242511bc145755cf4bda2485ade42966e096f8b4d3da2a230e8974'},
]
for tool in TOOLS:
    archive = Path('tools/downloads') / tool['url'].rsplit('/', 1)[-1]
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        partial = archive.with_suffix(archive.suffix + '.partial')
        urllib.request.urlretrieve(tool['url'], partial)
        partial.rename(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != tool['sha256']:
        raise SystemExit(f'{archive}: hash mismatch, do not execute')
    destination = Path('tools/bin') / tool['name']
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith('.zip'):
        with zipfile.ZipFile(archive) as z:
            z.extractall(destination)
    else:
        with tarfile.open(archive) as t:
            t.extractall(destination, filter='data')
    print(tool['name'], tool['version'], 'verified')
Path('analysis/evidence/tools.json').write_text(json.dumps({
    'windows_tools': TOOLS,
    'erofs_utils': {'version': '1.7.1-1build2',
        'source': 'Ubuntu noble/universe amd64 signed apt index',
        'sha256': 'ce1a7283a3ffc47bc832dfd77c4fba6a327f3928f1c90c64fe14e251251cfc3a',
        'install': 'apt download; dpkg-deb -x into tools/wsl/root; not installed globally'},
    'python': '3.14.6 (Windows)', 'java': 'Microsoft OpenJDK 17.0.9.8',
    'wsl': 'Ubuntu-24.04 / WSL2',
    'existing_android_tools': {
        'aapt2': 'SDK build-tools 37.0.0 / 2.20-15087165',
        'llvm_objdump': 'NDK 30.0.15729638 / LLVM 21.0.0',
        'installation': 'Already present in local Android SDK; no new SDK/NDK installation'},
    'note': 'JADX SHA256 recorded locally on first download; payload tool checksum also checked against upstream checksum asset',
}, indent=2) + '\n', encoding='utf-8')
