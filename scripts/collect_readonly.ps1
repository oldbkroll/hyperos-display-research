[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$Serial,
    [string]$Label = 'baseline',
    [string]$Adb = 'adb',
    [string]$OutputRoot = (Join-Path $PSScriptRoot '../analysis/local/device-validation')
)
$ErrorActionPreference = 'Stop'
if ($Label -notmatch '^[A-Za-z0-9_-]+$') { throw 'Label must contain only letters, numbers, _ or -' }
if (-not $PSCmdlet.ShouldProcess($Serial, "Collect read-only Android display diagnostics ($Label)")) { return }
$AdbCommand = Get-Command $Adb -ErrorAction SilentlyContinue
if (-not $AdbCommand) {
    $SdkAdb = Join-Path $env:LOCALAPPDATA 'Android/Sdk/platform-tools/adb.exe'
    if (-not (Test-Path -LiteralPath $SdkAdb)) { throw 'ADB not found; pass -Adb with its path' }
    $Adb = $SdkAdb
} else { $Adb = $AdbCommand.Source }
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Destination = Join-Path $OutputRoot "$Stamp-$Label"
if (Test-Path -LiteralPath $Destination) { throw 'Capture directory already exists' }
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Jobs = @(
    @{ Name = 'getprop'; Args = @('shell', 'getprop') },
    @{ Name = 'display'; Args = @('shell', 'dumpsys', 'display') },
    @{ Name = 'surfaceflinger'; Args = @('shell', 'dumpsys', 'SurfaceFlinger') },
    @{ Name = 'window-displays'; Args = @('shell', 'dumpsys', 'window', 'displays') },
    @{ Name = 'activities'; Args = @('shell', 'dumpsys', 'activity', 'activities') },
    @{ Name = 'input'; Args = @('shell', 'dumpsys', 'input') },
    @{ Name = 'thermal'; Args = @('shell', 'dumpsys', 'thermalservice') },
    @{ Name = 'overlay-help'; Args = @('shell', 'cmd', 'overlay', 'help') },
    @{ Name = 'overlay-list'; Args = @('shell', 'cmd', 'overlay', 'list', '--user', '0') },
    @{ Name = 'display-help'; Args = @('shell', 'cmd', 'display', 'help') },
    @{ Name = 'package-help'; Args = @('shell', 'cmd', 'package', 'help') },
    @{ Name = 'wm-help'; Args = @('shell', 'wm', 'help') },
    @{ Name = 'am-help'; Args = @('shell', 'am', 'help') },
    @{ Name = 'features'; Args = @('shell', 'pm', 'list', 'features') },
    @{ Name = 'home-package'; Args = @('shell', 'dumpsys', 'package', 'com.miui.home') },
    @{ Name = 'systemui'; Args = @('shell', 'dumpsys', 'activity', 'service', 'com.android.systemui/.SystemUIService') },
    @{ Name = 'secondary-home'; Args = @('shell', 'cmd', 'package', 'resolve-activity', '--brief', '--user', '0', '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.SECONDARY_HOME') },
    @{ Name = 'mirror'; Args = @('shell', 'settings', '--user', '0', 'get', 'secure', 'mirror_built_in_display') },
    @{ Name = 'external-connected'; Args = @('shell', 'settings', '--user', '0', 'get', 'system', 'external_display_connected') },
    @{ Name = 'force-desktop'; Args = @('shell', 'settings', 'get', 'global', 'force_desktop_mode_on_external_displays') },
    @{ Name = 'freeform'; Args = @('shell', 'settings', 'get', 'global', 'enable_freeform_support') },
    @{ Name = 'desktop-override'; Args = @('shell', 'settings', 'get', 'global', 'development_override_desktop_mode_features') },
    @{ Name = 'recent-logcat'; Args = @('shell', 'logcat', '-d', '-t', '2000') }
)
foreach ($Resource in @('config_isDesktopModeSupported', 'config_isDesktopModeDevOptionSupported', 'config_canInternalDisplayHostDesktops')) {
    $Jobs += @{ Name = "resource-$Resource"; Args = @('shell', 'cmd', 'overlay', 'lookup', '--user', '0', '--verbose', 'android', "android:bool/$Resource") }
}
$Results = @()
foreach ($Job in $Jobs) {
    $CommandArgs = $Job.Args
    $Output = Join-Path $Destination ($Job.Name + '.txt')
    try {
        # Each element is an argument; there is no string-built remote shell script.
        & $Adb -s $Serial @CommandArgs 2>&1 | Out-File -LiteralPath $Output -Encoding utf8
        $Results += @{ name = $Job.Name; args = $CommandArgs; exit_code = $LASTEXITCODE }
    } catch {
        $_ | Out-File -LiteralPath $Output -Encoding utf8
        $Results += @{ name = $Job.Name; args = $CommandArgs; error = $_.Exception.Message }
    }
}
@{ serial = $Serial; label = $Label; captured_at = (Get-Date -Format o); commands = $Results } |
    ConvertTo-Json -Depth 6 | Out-File -LiteralPath (Join-Path $Destination 'capture.json') -Encoding utf8
Write-Output "Saved local capture: $Destination"
