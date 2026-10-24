# Imports the project and runs the GUT unit tests headless.
# Usage: powershell -File tools/run_tests.ps1   (set $env:GODOT to use another Godot binary)
$ErrorActionPreference = "Stop"
$godot = if ($env:GODOT) { $env:GODOT } else { (Join-Path $env:USERPROFILE "Tools\Godot\Godot_v4.7.2-stable_win64_console.exe") }
$project = Split-Path -Parent $PSScriptRoot

& $godot --headless --path $project --import
& $godot --headless --path $project -s addons/gut/gut_cmdln.gd -gdir=res://tests -ginclude_subdirs -gexit
exit $LASTEXITCODE
