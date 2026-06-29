$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$condaPython = 'C:\Users\74749\miniforge3\envs\tianshui-gis\python.exe'
$venvPython = Join-Path $scriptDir '.venv\Scripts\python.exe'

if (Test-Path $condaPython) {
  $pythonExe = $condaPython
} elseif (Test-Path $venvPython) {
  $pythonExe = $venvPython
} else {
  throw "未找到可用的后端 Python 解释器。请先确认 GIS 环境已安装: $condaPython"
}

Set-Location $scriptDir
& $pythonExe manage.py runserver 127.0.0.1:8000
