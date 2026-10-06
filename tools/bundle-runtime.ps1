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
New-Item -ItemType Directory -Force "$resources/worker" | Out-Null
Copy-Item apps/api/worker.py "$resources/worker/worker.py"
Copy-Item -Recurse apps/api/vocalmorph "$resources/worker/vocalmorph"
Copy-Item "$Build/core/Release/vocalmorph_dsp.dll" "$runtime/vocalmorph_dsp.dll"
$python=Join-Path $runtime 'python.exe'
& $python -I -c "import torch, transformers, librosa, scipy, numpy, soundfile; print('Bundled inference dependencies OK')"
if ($LASTEXITCODE -ne 0) { throw 'Bundled runtime smoke test failed' }
# Preserve all third-party dist-info license files in the runtime.
