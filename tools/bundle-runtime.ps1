param([Parameter(Mandatory=$true)][string]$Stage,[Parameter(Mandatory=$true)][string]$Build)
$ErrorActionPreference='Stop'
$resources=Join-Path $Stage 'VocalMorph.vst3/Contents/Resources'
$runtime=Join-Path $resources 'runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$zip=Join-Path $env:RUNNER_TEMP 'python-3.12.10-embed-amd64.zip'
Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $zip
Expand-Archive $zip $runtime -Force
@('python312.zip','.', 'Lib/site-packages','import site') | Set-Content (Join-Path $runtime 'python312._pth') -Encoding ASCII
python -m pip install --only-binary=:all: --target "$runtime/Lib/site-packages" -r tools/runtime-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Bundled runtime dependency install failed' }
python tools/bootstrap.py
if ($LASTEXITCODE -ne 0) { throw 'RVC dependency checkout failed' }
$rvc=Join-Path $resources 'rvc'
New-Item -ItemType Directory -Force $rvc | Out-Null
foreach ($folder in @('infer','tools')) { Copy-Item -Recurse "third_party/rvc/$folder" "$rvc/$folder" }
Copy-Item third_party/rvc/LICENSE "$rvc/LICENSE"

# Bundle the common RVC support weights so users only need to choose a voice .pth.
# Sources/revisions are pinned and large binaries are checksum-verified.
$assets=Join-Path $resources 'assets'
$rmvpeDir=Join-Path $assets 'rmvpe'
$hubertDir=Join-Path $assets 'hubert_base'
New-Item -ItemType Directory -Force $rmvpeDir,$hubertDir | Out-Null

function Get-VerifiedFile {
 param([string]$Url,[string]$Path,[string]$Sha256='')
 & curl.exe -L --fail --retry 4 --retry-delay 2 --output $Path $Url
 if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
 if ($Sha256) {
  $actual=(Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne $Sha256.ToLowerInvariant()) {
   Remove-Item $Path -Force -ErrorAction SilentlyContinue
   throw "SHA-256 mismatch for $Path (got $actual)"
  }
 }
}

$rmvpeRevision='0658a97f086c16951f55b4349c0b25503b6ffdba'
$rmvpeFile=Join-Path $rmvpeDir 'rmvpe.pt'
Get-VerifiedFile "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/$rmvpeRevision/rmvpe.pt?download=true" $rmvpeFile '6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193'

$hubertRevision='1be9d36ece685661920e1a7cb36eb0437c1e5581'
Get-VerifiedFile "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/$hubertRevision/hubert_base/config.json?download=true" (Join-Path $hubertDir 'config.json')
Get-VerifiedFile "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/$hubertRevision/hubert_base/preprocessor_config.json?download=true" (Join-Path $hubertDir 'preprocessor_config.json')
Get-VerifiedFile "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/$hubertRevision/hubert_base/pytorch_model.bin?download=true" (Join-Path $hubertDir 'pytorch_model.bin') 'cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5'

@"
Bundled RVC support weights
Source: https://huggingface.co/lj1995/VoiceConversionWebUI
Repository license: MIT
RMVPE revision: $rmvpeRevision
RMVPE SHA-256: 6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193
HuBERT revision: $hubertRevision
HuBERT pytorch_model.bin SHA-256: cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5
"@ | Set-Content (Join-Path $assets 'WEIGHTS-NOTICE.txt') -Encoding UTF8
New-Item -ItemType Directory -Force "$resources/worker" | Out-Null
Copy-Item apps/api/worker.py "$resources/worker/worker.py"
Copy-Item -Recurse apps/api/vocalmorph "$resources/worker/vocalmorph"
Copy-Item "$Build/core/Release/vocalmorph_dsp.dll" "$runtime/vocalmorph_dsp.dll"
$python=Join-Path $runtime 'python.exe'
& $python -I -c "import torch, transformers, librosa, scipy, numpy, soundfile; print('Bundled inference dependencies OK')"
if ($LASTEXITCODE -ne 0) { throw 'Bundled runtime smoke test failed' }
& $python -I -c "import sys; sys.path.insert(0, r'$rvc'); from infer.rmvpe import RMVPE; RMVPE(r'$rmvpeFile', is_half=False, device='cpu'); print('Bundled RMVPE weight OK')"
if ($LASTEXITCODE -ne 0) { throw 'Bundled RMVPE smoke test failed' }
# Preserve all third-party dist-info license files in the runtime.
