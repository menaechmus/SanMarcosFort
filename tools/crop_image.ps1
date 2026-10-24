# Crops a region of a large image (e.g. a HABS TIFF master) and saves it as PNG.
# The region is given in percent of the image: x, y, width, height.
# Usage: powershell -File tools/crop_image.ps1 -In sheet.tif -Region 30,25,30,40 -Width 1600 -Out crop.png
param(
    [Parameter(Mandatory = $true)][string]$In,
    [Parameter(Mandatory = $true)][string]$Region,
    [int]$Width = 1600,
    [Parameter(Mandatory = $true)][string]$Out
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$box = @($Region -split "," | ForEach-Object { [double]$_ })

$source = [System.Drawing.Image]::FromFile((Resolve-Path $In))
try {
    $x = [int]($source.Width * $box[0] / 100)
    $y = [int]($source.Height * $box[1] / 100)
    $w = [int]($source.Width * $box[2] / 100)
    $h = [int]($source.Height * $box[3] / 100)
    $height = [int]($Width * $h / $w)
    $target = New-Object System.Drawing.Bitmap $Width, $height
    $g = [System.Drawing.Graphics]::FromImage($target)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.Clear([System.Drawing.Color]::White)
    $g.DrawImage($source, (New-Object System.Drawing.Rectangle 0, 0, $Width, $height), $x, $y, $w, $h, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    $target.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    $target.Dispose()
    Write-Host ("{0}: {1}x{2} px from source {3}x{4}" -f $Out, $Width, $height, $source.Width, $source.Height)
}
finally {
    $source.Dispose()
}
