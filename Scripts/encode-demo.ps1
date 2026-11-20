param([Parameter(Mandatory=$true)][ValidateSet('02-01','02-02','02-03','02-04')][string]$Stage)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$framesRoot = Join-Path $projectRoot "Saved/Demos/$Stage"
$capture = Get-Content -LiteralPath (Join-Path $framesRoot 'capture.json') -Raw | ConvertFrom-Json
if ($capture.status -ne 'captured' -or $capture.frames -lt 20) { throw 'A complete PIE capture is required' }
$manifest = [System.Collections.Generic.List[string]]::new()
$manifest.Add('ffconcat version 1.0')
for ($frameIndex=0; $frameIndex -lt $capture.frames; $frameIndex++) {
    $frameName = 'frame-{0:D4}.png' -f $frameIndex
    if (!(Test-Path -LiteralPath (Join-Path $framesRoot $frameName))) { throw "Missing $frameName" }
    $nextTime = if ($frameIndex+1 -lt $capture.frames) { $capture.frame_times[$frameIndex+1] } else { $capture.duration+0.125 }
    $seconds = [Math]::Max(0.01, $nextTime-$capture.frame_times[$frameIndex])
    $manifest.Add("file '$frameName'")
    $manifest.Add('duration ' + $seconds.ToString('0.000000',[Globalization.CultureInfo]::InvariantCulture))
}
$manifest.Add("file '$frameName'")
$manifestPath = Join-Path $framesRoot 'capture.ffconcat'
[IO.File]::WriteAllLines($manifestPath, $manifest, [Text.UTF8Encoding]::new($false))
$outputFolder = Join-Path $projectRoot 'Docs/GIF'
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
$outputPath = Join-Path $outputFolder "$Stage.gif"
& ffmpeg -hide_banner -loglevel error -y -safe 0 -f concat -i $manifestPath -filter_complex '[0:v]fps=8,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none' -loop 0 $outputPath
if ($LASTEXITCODE -ne 0) { throw 'GIF encoding failed' }
Get-Item -LiteralPath $outputPath | Select-Object FullName,Length
