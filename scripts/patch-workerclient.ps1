param([Parameter(Mandatory=$true)][string]$RvcRoot)

$ErrorActionPreference = "Stop"

$path = Join-Path $RvcRoot "RVCRealtimeVST\src\WorkerClient.cpp"
$src = Get-Content $path -Raw

$needle = "std::wstring workerScriptPath()" + [Environment]::NewLine + "{"
$helper = @"
std::wstring resourcesDirectory()
{
    const std::wstring directory = moduleDirectory();
    if (directory.empty())
        return {};
    const std::wstring vst3 = directory + L"\\..\\Resources";
    const DWORD attrs = GetFileAttributesW(vst3.c_str());
    if (attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_DIRECTORY) != 0)
        return vst3;
    return directory + L"\\" + utf8ToWide(RVC_VST2_RESOURCES_DIR);
}

std::wstring workerScriptPath()
{
"@
if (-not $src.Contains($needle)) { throw "workerScriptPath marker not found" }
$src = $src.Replace($needle, $helper.TrimEnd())

$old = '    std::ostringstream json;' + [Environment]::NewLine + '    json << "{\n"' + [Environment]::NewLine + '         << "  \"rvc_root\": \"" << jsonEscape(paths.rvcRoot) << "\",\n"'
$new = '    const std::string bundledRoot = wideToUtf8(resourcesDirectory() + L"\\rvc");' + [Environment]::NewLine + '    std::ostringstream json;' + [Environment]::NewLine + '    json << "{\n"' + [Environment]::NewLine + '         << "  \"rvc_root\": \"" << jsonEscape(bundledRoot) << "\",\n"'
if (-not $src.Contains($old)) { throw "worker config marker not found" }
$src = $src.Replace($old,$new)

$src = $src.Replace('    std::string command = quoteArg(paths.python) + " -I " + quoteArg(wideToUtf8(workerScript))', '    const std::string bundledPython = wideToUtf8(resourcesDirectory() + L"\\runtime\\python.exe");' + [Environment]::NewLine + '    std::string command = quoteArg(bundledPython) + " -I " + quoteArg(wideToUtf8(workerScript))')
$src = $src.Replace('    const std::wstring cwd = utf8ToWide(paths.rvcRoot);', '    const std::wstring cwd = resourcesDirectory() + L"\\rvc";')
$src = $src.Replace('    const std::wstring application = utf8ToWide(paths.python);', '    const std::wstring application = resourcesDirectory() + L"\\runtime\\python.exe";')

Set-Content -Path $path -Value $src -Encoding UTF8
Write-Host "WorkerClient patched for bundled runtime."