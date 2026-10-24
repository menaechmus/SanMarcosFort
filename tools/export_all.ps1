# Exports each preset into build/<platform>/.
# Usage: powershell -File tools/export_all.ps1 [Web|Windows|Android]   (no argument = all)
# Set $env:GODOT to use another Godot binary.
# Android is exported as a debug build (signed with the debug keystore set in the editor
# settings) unless GODOT_ANDROID_KEYSTORE_RELEASE_PATH, _USER and _PASSWORD are set; see README.
param([string[]]$Only = @())
$ErrorActionPreference = "Stop"
$godot = if ($env:GODOT) { $env:GODOT } else { (Join-Path $env:USERPROFILE "Tools\Godot\Godot_v4.7.2-stable_win64_console.exe") }
$project = Split-Path -Parent $PSScriptRoot
$androidMode = if ($env:GODOT_ANDROID_KEYSTORE_RELEASE_PATH) { "release" } else { "debug" }

$presets = @(
    @{ Key = "Web"; Name = "Web"; Out = "build/web/index.html"; Mode = "release" },
    @{ Key = "Windows"; Name = "Windows Desktop"; Out = "build/windows/SanMarcosFort.exe"; Mode = "release" },
    @{ Key = "Android"; Name = "Android"; Out = "build/android/SanMarcosFort.apk"; Mode = $androidMode }
)

& $godot --headless --path $project --import
# Keep Godot from importing exported files as project assets.
New-Item -ItemType Directory -Force (Join-Path $project "build") | Out-Null
New-Item -ItemType File -Force (Join-Path $project "build/.gdignore") | Out-Null
foreach ($preset in $presets) {
    if ($Only.Count -gt 0 -and $Only -notcontains $preset.Key) { continue }
    $out = Join-Path $project $preset.Out
    New-Item -ItemType Directory -Force (Split-Path -Parent $out) | Out-Null
    Write-Host "Exporting $($preset.Name) ($($preset.Mode)) -> $out"
    & $godot --headless --path $project "--export-$($preset.Mode)" $preset.Name $out
    if ($LASTEXITCODE -ne 0) { throw "Export failed for $($preset.Name)" }
}
