# Windows x64 installation and build

Download the Actions artifact, extract its inner ZIP, and copy the **entire VocalMorph.vst3 folder** to `C:\Program Files\Common Files\VST3`. Do not move only the inner DLL. Rescan VST3 plugins in your DAW. The Resources directory contains the offline Python runtime; no separate Python installation or RVC server is required for the packaged plugin.

Build locally using Visual Studio 2022 Desktop development with C++, Windows SDK, CMake 3.24+, Git and Python 3.12:

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release --parallel 4
ctest --test-dir build -C Release --output-on-failure
cmake --install build --config Release --prefix release/stage
$env:RUNNER_TEMP = [System.IO.Path]::GetTempPath()
./tools/bundle-runtime.ps1 -Stage "$pwd/release/stage" -Build "$pwd/build"
```

Select a licensed `model.pth` with its adjacent manifest and base assets. Activate Neural live mode to run the worker. DSP monitoring reports zero algorithmic latency (pitch shifting adds a variable short delay). Neural live reports 640 ms and falls back to delayed dry audio if CPU processing is late. Use the web offline transform for high-quality final renders; DAW accelerated offline neural rendering is not yet supported.
