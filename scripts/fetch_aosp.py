"""Cache a pinned Android 17 reference; source remains local, publish hashes only."""
import base64
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

COMMIT = '94b4c163b7dfe5ce3607f7bb8456f9573f7de57d'
FILES = [
    'services/core/java/com/android/server/display/DisplayManagerService.java',
    'services/core/java/com/android/server/display/LogicalDisplayMapper.java',
    'services/core/java/com/android/server/display/LocalDisplayAdapter.java',
    'services/core/java/com/android/server/display/mode/DisplayModeDirector.java',
    'services/core/java/com/android/server/wm/ActivityTaskManagerService.java',
    'services/core/java/com/android/server/wm/ActivityTaskSupervisor.java',
    'services/core/java/com/android/server/wm/RootWindowContainer.java',
    'services/core/java/com/android/server/wm/DisplayContent.java',
    'services/core/java/com/android/server/wm/DisplayPolicy.java',
    'services/core/java/com/android/server/wm/WindowManagerService.java',
    'core/java/android/app/ActivityOptions.java',
    'core/java/android/window/DesktopModeFlags.java',
    'core/java/com/android/internal/policy/DesktopModeCompatUtils.java',
    'services/core/java/com/android/server/wm/DesktopModeHelper.java',
    'services/core/java/com/android/server/display/SecondaryDisplayPolicy.java',
    'services/core/java/com/android/server/wm/DisplayWindowSettings.java',
    'services/core/java/com/android/server/input/InputManagerService.java',
    'core/res/res/values/config.xml',
    'packages/SystemUI/AndroidManifest.xml',
    'libs/WindowManager/Shell/shared/src/com/android/wm/shell/shared/desktopmode/DesktopState.kt',
    'libs/WindowManager/Shell/src/com/android/wm/shell/desktopmode/DesktopTasksController.kt',
    'libs/WindowManager/Shell/src/com/android/wm/shell/desktopmode/DesktopDisplayEventHandler.kt',
]


def fetch(path):
    url = f'https://android.googlesource.com/platform/frameworks/base/+/{COMMIT}/{path}'
    target = Path('analysis/local/aosp') / path
    try:
        if not target.exists():
            data = base64.b64decode(urllib.request.urlopen(url + '?format=TEXT', timeout=45).read())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        data = target.read_bytes()
        return {'path': path, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(),
                'lines': len(data.splitlines()), 'status': 'ok'}
    except Exception as exc:
        return {'path': path, 'url': url, 'status': 'failed', 'error': str(exc)}


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, FILES))
    Path('analysis/evidence/aosp-sources.json').write_text(json.dumps({
        'branch_at_selection': 'android17-release', 'commit': COMMIT,
        'warning': 'Reference branch is not proven to match Xiaomi source revision',
        'files': results}, indent=2) + '\n', encoding='utf-8')
    for result in results:
        print(result['status'], result['path'], result.get('error', ''))
