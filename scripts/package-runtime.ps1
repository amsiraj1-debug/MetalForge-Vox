param(
  [Parameter(Mandatory=$true)][string]$RvcRoot,
  [Parameter(Mandatory=$true)][string]$Vst3Path
)

$ErrorActionPreference = "Stop"

$resources = Join-Path $Vst3Path "Contents\Resources"
$runtimeDir = Join-Path $resources "runtime"
$rvcDir = Join-Path $resources "rvc"
$workerDir = Join-Path $resources "worker"
New-Item -ItemType Directory -Force -Path $runtimeDir,$rvcDir,$workerDir | Out-Null

Copy-Item -Force (Join-Path $RvcRoot "RVCRealtimeVST\worker\rvc_worker.py") (Join-Path $workerDir "rvc_worker.py")

foreach ($d in @("configs","infer","tools","i18n","assets")) {
  $src = Join-Path $RvcRoot $d
  if (Test-Path $src) { Copy-Item -Recurse -Force $src (Join-Path $rvcDir $d) }
}

$pyVersion = "3.12.10"
$pyZip = Join-Path $env:RUNNER_TEMP "python-$pyVersion-embed-amd64.zip"
Invoke-WebRequest "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-embed-amd64.zip" -OutFile $pyZip
Expand-Archive -Force $pyZip $runtimeDir

$pth = Get-ChildItem $runtimeDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pth) { throw "Embedded Python ._pth file not found" }
$txt = Get-Content $pth.FullName -Raw
$txt = $txt.Replace("#import site","import site")
Set-Content -Path $pth.FullName -Value $txt -Encoding ASCII

$getPip = Join-Path $env:RUNNER_TEMP "get-pip.py"
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
$py = Join-Path $runtimeDir "python.exe"
& $py $getPip
if ($LASTEXITCODE -ne 0) { throw "pip bootstrap failed" }

& $py -m pip install --upgrade "pip<26" "setuptools<81" wheel
if ($LASTEXITCODE -ne 0) { throw "pip setup failed" }

$deps = @(
  "torch==2.4.1+cpu",
  "torchaudio==2.4.1+cpu",
  "transformers>=4.49,<4.50",
  "numpy>=1.26.4,<2",
  "scipy>=1.13.1,<2",
  "librosa>=0.10.2,<0.11",
  "faiss-cpu>=1.13,<2",
  "praat-parselmouth>=0.4.5,<1",
  "torchfcpe>=0.0.4,<0.1",
  "soundfile>=0.13,<1",
  "PyYAML>=6",
  "einops>=0.8,<1",
  "local-attention>=1.11,<2",
  "hyper-connections>=0.1.8,<0.4.3"
)
& $py -m pip install --extra-index-url "https://download.pytorch.org/whl/cpu" @deps
if ($LASTEXITCODE -ne 0) { throw "Runtime dependency installation failed" }

@("Bundled CPU RVC runtime","RVC source commit: 81eed5e8f68b6bed1789f682fe78cdd324495afc","Load your own/authorized .pth model and optional .index file in MetalForge Vox.") | Set-Content -Path (Join-Path $resources "METALFORGE_RUNTIME.txt") -Encoding UTF8

Write-Host "Bundled runtime created at $resources"