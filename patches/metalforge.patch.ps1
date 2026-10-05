$ErrorActionPreference = "Stop"

param(
  [Parameter(Mandatory=$true)][string]$RvcRoot
)

$vst = Join-Path $RvcRoot "RVCRealtimeVST"
$config = Join-Path $vst "config.h"
$cpp = Join-Path $vst "src\RVCRealtime.cpp"

if (-not (Test-Path $config)) { throw "Missing $config" }
if (-not (Test-Path $cpp)) { throw "Missing $cpp" }

$c = Get-Content $config -Raw
$c = $c.Replace('#define PLUG_NAME "RVC Realtime"', '#define PLUG_NAME "MetalForge Vox"')
$c = $c.Replace('#define PLUG_MFR "RVC Project"', '#define PLUG_MFR "MetalForge"')
$c = $c.Replace('#define PLUG_VERSION_STR "0.1.0"', '#define PLUG_VERSION_STR "0.1.0-mf"')
$c = $c.Replace("#define PLUG_UNIQUE_ID 'Rvcr'", "#define PLUG_UNIQUE_ID 'Mfvx'")
$c = $c.Replace("#define PLUG_MFR_ID 'Rvcp'", "#define PLUG_MFR_ID 'Mtfg'")
$c = $c.Replace('#define BUNDLE_NAME "RVCRealtime"', '#define BUNDLE_NAME "MetalForgeVox"')
$c = $c.Replace('#define BUNDLE_MFR "RVCProject"', '#define BUNDLE_MFR "MetalForge"')
$c = $c.Replace('#define SHARED_RESOURCES_SUBPATH "RVCRealtime"', '#define SHARED_RESOURCES_SUBPATH "MetalForgeVox"')
Set-Content -Path $config -Value $c -Encoding UTF8

$src = Get-Content $cpp -Raw
$src = $src.Replace('graphics->AttachControl(new ITextControl(IRECT(28, 10, 420, 52), "RVC REALTIME",',
                    'graphics->AttachControl(new ITextControl(IRECT(28, 10, 420, 52), "METALFORGE VOX",')
$src = $src.Replace('"VOICE CONVERSION / CUDA BRIDGE"', '"RVC VOICE CONVERSION / BUNDLED RUNTIME"')
$src = $src.Replace('attachFileRow(100.f, "RVC ROOT", kCtrlRvcRoot, PathRow::RvcRoot);', '')
$src = $src.Replace('attachFileRow(142.f, "PYTHON", kCtrlPythonPath, PathRow::Python);', '')
$src = $src.Replace('attachFileRow(184.f, "MODEL", kCtrlModelName, PathRow::Model);',
                    'attachFileRow(142.f, "MODEL", kCtrlModelName, PathRow::Model);')
$src = $src.Replace('attachFileRow(226.f, "INDEX", kCtrlIndexName, PathRow::Index);',
                    'attachFileRow(184.f, "INDEX", kCtrlIndexName, PathRow::Index);')
$src = $src.Replace('IRECT(96, 266, 750, 290), "Select RVC root and Python runtime"',
                    'IRECT(96, 226, 750, 250), "Bundled RVC runtime - select .pth and optional .index"')
$src = $src.Replace('const float gridLeft = 30.f, gridTop = 300.f;', 'const float gridLeft = 30.f, gridTop = 270.f;')
$src = $src.Replace('const float bottomY = 566.f, bottomHeight = 44.f;', 'const float bottomY = 536.f, bottomHeight = 44.f;')
Set-Content -Path $cpp -Value $src -Encoding UTF8

Write-Host "MetalForge Vox patch applied."
