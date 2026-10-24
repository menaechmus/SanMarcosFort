# Rebuilds every generated 3D model with Blender (headless), plus preview renders.
# Usage: powershell -File tools/build_assets.ps1 [fort] [terrain] [cannon] [ships] [props]   (no argument = all)
# Set $env:BLENDER to use another Blender executable.
param([string[]]$Only = @())
$ErrorActionPreference = "Stop"
$blender = if ($env:BLENDER) { $env:BLENDER } else { "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" }
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project

$jobs = [ordered]@{
    fort    = @("tools/blender/build_fort.py", "--out", "assets/models/fort/fort.glb", "--blend", "build/blend/fort.blend", "--preview", "build/previews/fort")
    terrain = @("tools/blender/build_terrain.py", "--out", "assets/models/terrain/terrain.glb", "--blend", "build/blend/terrain.blend", "--preview", "build/previews/terrain")
    cannon  = @("tools/blender/build_cannon.py", "--out", "assets/models/cannon/cannon.glb", "--blend", "build/blend/cannon.blend", "--preview", "build/previews/cannon")
    ships   = @("tools/blender/build_ships.py", "--out-dir", "assets/models/ships", "--blend-dir", "build/blend", "--preview-dir", "build/previews/ships")
    props   = @("tools/blender/build_props.py", "--out", "assets/models/props/props.glb", "--scatter", "assets/models/props/props_scatter.tres", "--blend", "build/blend/props.blend", "--preview", "build/previews/props")
}

foreach ($name in $jobs.Keys) {
    if ($Only.Count -gt 0 -and $Only -notcontains $name) { continue }
    $script, $rest = $jobs[$name]
    Write-Host "== $name"
    $output = & $blender -b --factory-startup -P $script -- @rest 2>&1 | Out-String
    $lines = $output.Split("`n") | Where-Object { $_ -match '^\[|Error|Traceback|File "' }
    $lines | ForEach-Object { Write-Host "   $_" }
    if ($output -match "Traceback") { throw "Blender build failed: $name" }
}
