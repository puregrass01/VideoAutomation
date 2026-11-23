# Korean Windows OCR over every PNG/JPG in a folder (youtube_lines.py calls this once per video).
# Prints one JSON line per image: {"file": name, "w": px, "h": px, "lines": [{"text", "x", "y", "w", "h"}]}.
param([Parameter(Mandatory)][string]$Dir)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(); $task.Result }

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('ko'))
if (-not $engine) { throw 'Korean OCR language is not installed (Settings > Time & language > Language > Korean)' }
Get-ChildItem -LiteralPath $Dir -File | Where-Object { $_.Extension -in '.png', '.jpg' } | Sort-Object Name | ForEach-Object {
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($_.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = foreach ($line in $result.Lines) {
        $r = $line.Words | ForEach-Object { $_.BoundingRect }
        $x = ($r | Measure-Object X -Minimum).Minimum; $y = ($r | Measure-Object Y -Minimum).Minimum
        $x2 = ($r | ForEach-Object { $_.X + $_.Width } | Measure-Object -Maximum).Maximum
        $y2 = ($r | ForEach-Object { $_.Y + $_.Height } | Measure-Object -Maximum).Maximum
        [ordered]@{ text = $line.Text; x = [int]$x; y = [int]$y; w = [int]($x2 - $x); h = [int]($y2 - $y) }
    }
    $stream.Dispose()
    [ordered]@{ file = $_.Name; w = $bitmap.PixelWidth; h = $bitmap.PixelHeight; lines = @($lines) } | ConvertTo-Json -Compress -Depth 4
}
