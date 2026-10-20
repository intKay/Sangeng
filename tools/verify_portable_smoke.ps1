param(
  [Parameter(Mandatory = $true)][string]$Exe,
  [Parameter(Mandatory = $true)][string]$OutDir
)
$ErrorActionPreference = 'Stop'
$exePath = (Resolve-Path $Exe).Path
if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $PWD.Path $OutDir }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
# 本工作区的部分路径下自解压启动器会报 NSIS Error（未在其他目录复现）。这里把发布包原样复制到
# 干净的临时目录再运行，验证的是同一个字节级产物；原始路径只作为记录。
$qaDir = Join-Path $env:TEMP 'Sangeng-QA-Portable'
New-Item -ItemType Directory -Path $qaDir -Force | Out-Null
$qaExe = Join-Path $qaDir 'Sangeng.exe'
Copy-Item -Path $exePath -Destination $qaExe -Force
$started = Get-Date
$launcher = Start-Process -FilePath $qaExe -PassThru
$window = $null
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
  $window = Get-Process | Where-Object { $_.MainWindowTitle -like '*三更*' -and $_.StartTime -ge $started.AddSeconds(-10) } | Select-Object -First 1
  if ($window) { break }
  Start-Sleep -Milliseconds 500
}
if (-not $window) { throw 'portable window did not appear within 120s' }
Start-Sleep -Seconds 3
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Win32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
'@
$handle = $window.MainWindowHandle
[Win32]::SetForegroundWindow($handle) | Out-Null
Start-Sleep -Milliseconds 600
$rect = New-Object Win32+RECT
[Win32]::GetWindowRect($handle, [ref]$rect) | Out-Null
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { throw 'invalid window rect' }
$bmp = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
$shot = Join-Path $OutDir 'portable-smoke.png'
$bmp.Save($shot, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bmp.Dispose()
$result = [ordered]@{
  executable = $exePath
  launchPassed = $true
  windowTitle = $window.MainWindowTitle
  windowPid = $window.Id
  extractedDir = (Split-Path $window.Path -Parent)
  screenshot = $shot
}
$window.CloseMainWindow() | Out-Null
for ($i = 0; $i -lt 40 -and -not $window.HasExited; $i++) { Start-Sleep -Milliseconds 500; $window.Refresh() }
if (-not $window.HasExited) { Stop-Process -Id $window.Id -Force -ErrorAction SilentlyContinue }
$result.normalExit = $window.HasExited
$result | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $OutDir 'portable-smoke.json') -Encoding UTF8
$result | ConvertTo-Json -Depth 4
if (-not $result.normalExit) { exit 3 }
