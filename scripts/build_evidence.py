"""Publish compact, original findings with hashes/anchors, never decompiled code."""
import hashlib
import json
from pathlib import Path
import re

anchors = [
    ('F01', 'services-numeric', 'com/android/server/wm/DesktopModeHelper.java',
     ['private static final boolean ENFORCE_DEVICE_RESTRICTIONS', 'private static boolean isDesktopModeSupported(', 'static boolean isDesktopModeDevOptionsSupported(', 'public static boolean canEnterDesktopMode(']),
    ('F02', 'services', 'com/android/server/display/DisplayManagerService.java',
     ['this.mSecondaryDisplayPolicy = new SecondaryDisplayPolicy', 'forceEnableMirrorBuiltInDisplaySettingIfNeeded()', 'return DesktopModeHelper.canEnterDesktopMode(context);']),
    ('F03', 'services', 'com/android/server/display/SecondaryDisplayPolicy.java',
     ['public boolean forceEnableMirrorBuiltInDisplaySettingIfNeeded()', 'private boolean shouldForceEnableMirrorBuiltInDisplaySetting()', 'private void enableMirrorBuiltInDisplaySetting()']),
    ('F04', 'framework-hidden-flags', 'com/android/internal/hidden_from_bootclasspath/com/android/window/flags/Flags.java',
     ['public static boolean enableDesktopWindowingMode()', 'public static boolean enableDesktopModeThroughDevOption()', 'public static boolean enableProjectedDisplayDesktopMode()', 'public static boolean showDesktopExperienceDevOption()']),
    ('F05', 'framework-hidden-flags', 'com/android/internal/hidden_from_bootclasspath/com/android/server/display/feature/flags/Flags.java',
     ['public static boolean enableDisplayContentModeManagement()']),
    ('F06', 'framework-selected', 'android/window/DesktopExperienceFlags.java',
     ['public static final String SYSTEM_PROPERTY_NAME', 'private static boolean isToggleOverriddenBySystem()', 'private static boolean isDesktopModeDevOptionSupported()']),
    ('F07', 'miui-shell', 'com/android/wm/shell/shared/desktopmode/DesktopStateImpl.java',
     ['public DesktopStateImpl(Context context)', 'this.canEnterDesktopMode =', 'public final boolean isDesktopModeSupportedOnDisplay(Display display)', 'public final boolean isDeviceEligibleForDesktopMode()']),
    ('F08', 'miui-shell', 'com/android/wm/shell/dagger/WMShellModule.java',
     ['public static Optional provideDesktopDisplayEventHandler(', 'public static Optional provideDesktopDisplayModeController(', 'public static Optional provideDesktopTasksLimiter(']),
    ('F09', 'services-numeric', 'com/android/server/wm/ActivityTaskSupervisor.java',
     ['boolean isCallerAllowedToLaunchOnDisplay(', 'if (display.getDisplayId() == 1']),
    ('F10', 'miui-services', 'com/android/server/wm/DisplayContentStubImpl.java',
     ['public boolean desktopModeForceDisabled(', 'public boolean shouldNeverShowSystemDecorations(']),
    ('F11', 'services', 'com/android/server/wm/DisplayContent.java',
     ['boolean allowContentModeSwitch()', 'boolean isPublicSecondaryDisplayWithDesktopModeForceEnabled()', 'public boolean isEligibleForDesktopMode()']),
    ('F12', 'miui-display-mode', 'com/android/server/display/mode/DisplayModeDirectorImpl.java',
     ['this.mBspSupportExtraDisplayHigRefreshRate =', 'public boolean updateMiuiRefreshRateSettingLocked(', 'private SurfaceControl.RefreshRateRange getMiuiRefreshRateRange()', 'private boolean shouldExtraDisplayLimitRefresh()', 'private boolean shouldConvertRefreshForDpHigh()', 'private boolean queryExternalDisplayEnabled()']),
    ('F13', 'services', 'com/android/server/display/mode/VotesStorage.java',
     ['SparseArray<Vote> getVotes(int displayId)', 'void updateGlobalVote(']),
    ('F14', 'services', 'com/android/server/display/mode/RefreshRateVote.java',
     ['static class RenderVote', 'static class PhysicalVote']),
    ('F15', 'services', 'com/android/server/display/ExternalDisplayPolicy.java',
     ['boolean isDisplayReadyForMirroring(int displayId)']),
    ('F16', 'miui-shell-extra', 'com/android/wm/shell/multitasking/stubs/miuidesktopmode/MiuiDesktopModeStatus.java',
     ['private static final boolean IS_SUPPORTED', 'public static boolean isEnabled()']),
    ('F17', 'services-numeric', 'com/android/server/wm/RootWindowContainer.java',
     ['boolean shouldPlaceSecondaryHomeOnDisplayArea(']),
    ('F18', 'services-atms-numeric', 'com/android/server/wm/ActivityTaskManagerService.java',
     ['Intent getSecondaryHomeIntent(']),
    ('F19', 'miui-registrations', 'com/android/server/display/mode/DisplayModeDirectorImpl$$GeneratedMiuiImplManifest.java',
     ['outProviders.put("com.android.server.display.DisplayManagerServiceStub"', 'outProviders.put("com.android.server.display.mode.DisplayModeDirectorStub"']),
    ('F20', 'miui-wm-registrations', 'com/android/server/wm/WindowStateStubImpl$$GeneratedMiuiImplManifest.java',
     ['outProviders.put("com.android.server.wm.DisplayContentStub"', 'outProviders.put("com.android.server.wm.ActivityStarterStub"', 'outProviders.put("com.android.server.wm.ExternalScreenCompatManagerStub"']),
    ('F21', 'miui-external', 'com/android/server/wm/ExternalScreenCompatManagerImpl.java',
     ['private final boolean mEnabled =', 'public boolean shouldApplyScaling(', 'public boolean applyScaleConfiguration(']),
    ('F22', 'miui-external', 'com/android/server/display/DisplayAdapterImpl.java',
     ['public void updateExternalDisplayStatus(']),
    ('F23', 'services', 'com/android/server/display/mode/DisplayModeDirector.java',
     ['this.mDisplayModeDirectorImpl = DisplayModeDirectorStub.getInstance();', 'registerMiuiContentObserver(cr, this)', 'public void updateMiuiRefreshRateSettingLocked()']),
]
methods = []
for ident, output, relative, signatures in anchors:
    path = Path('analysis/local/jadx') / output / 'sources' / relative
    data = path.read_bytes()
    lines = data.decode('utf-8').splitlines()
    locations = []
    for signature in signatures:
        matches = [i for i, line in enumerate(lines, 1) if signature in line]
        if not matches:
            raise SystemExit(f'Missing evidence anchor {ident}: {signature}')
        locations.append({'anchor': signature, 'lines': matches})
    methods.append({'id': ident, 'class': relative.removesuffix('.java').replace('/', '.'),
                    'local_output': path.as_posix(), 'decompiled_file_sha256': hashlib.sha256(data).hexdigest(),
                    'anchors': locations})

dump = Path('analysis/local/framework-res-aapt2.txt').read_text(encoding='utf-8')
resource_names = ['config_isDesktopModeSupported', 'config_isDesktopModeDevOptionSupported',
                  'config_canInternalDisplayHostDesktops', 'config_supportsMultiDisplay',
                  'config_supportsMultiWindow', 'config_supportsSystemDecorsOnSecondaryDisplays',
                  'config_secondaryHomePackage', 'config_useSystemProvidedLauncherForSecondary']
resources = []
lines = dump.splitlines()
for i, line in enumerate(lines):
    if any(re.search(r'/' + re.escape(name) + r'$', line) for name in resource_names):
        resources.append({'header': line.strip(), 'line': i + 1,
                          'default_value': lines[i + 1].strip()})

state = json.loads(Path('extracted/native-files.json').read_text())
properties = []
keys = {'ro.mi.os.version.incremental', 'ro.mi.os.version.name', 'ro.mi.os.version.code',
        'vendor.display.support_builtin_high_fps_when_pluggable_connected',
        'vendor.display.pluggable_vsync_prioritized', 'persist.sys.secondary_builtin_display_id',
        'persist.sys.multi_display_type', 'ro.vendor.display.default_fps',
        'ro.vendor.mi_sf.supported_automode_maxfps_list'}
for partition, record in state.items():
    # Read just build.prop paths from the native inventory, no directory walk over UNC.
    inventory = json.loads(Path('analysis/local/file-inventory.json').read_text())
    for entry in inventory:
        if entry['path'].startswith(partition + '/') and entry['path'].endswith('/build.prop'):
            relative = entry['path'].split('/', 1)[1]
            path = Path(record['windows_path']) / relative
            for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                if '=' in line and line.split('=', 1)[0] in keys:
                    key, value = line.split('=', 1)
                    properties.append({'path': entry['path'], 'line': number, 'key': key, 'value': value,
                                       'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
Path('analysis/evidence/findings.json').write_text(json.dumps({
    'scope': 'Static ROM evidence only; method anchors refer to local decompiler output, not original source lines',
    'methods': methods, 'base_resources': resources, 'properties': properties,
    'jadx_limitations': {'services_full_errors': 73, 'services_numeric_errors': 3,
        'miui_services_errors': 1, 'miui_shell_errors': 12, 'systemui_selected_errors': 1,
        'services_gate_fallback_errors': 0,
        'miui_display_mode_errors': 0, 'atms_numeric_errors': 6,
        'miui_external_errors': 0,
        'note': 'Counts are per run, not a proof all methods are reliable. Failed unrelated methods are not evidence.'},
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Saved', len(methods), 'method records,', len(resources), 'resources,', len(properties), 'properties')
