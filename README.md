# VocalMorph

Original Windows vocal studio: Next.js web app, asynchronous FastAPI backend, reusable C++ DSP, and JUCE VST3 with a bundled offline PyTorch/RVC worker.

**Development build, not a production-certified voice converter.** No voice or base-model weights are distributed. Install a licensed model package before using neural conversion. DSP styles work immediately. See docs/STATUS.md for verified functionality and limitations.

## Web studio

Requires Node 22, Python 3.12, CMake 3.24+, Visual Studio 2022 C++ tools on Windows.

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DVM_BUILD_PLUGIN=OFF
cmake --build build --config Release --parallel
python -m pip install -r apps/api/requirements-ai.txt
python tools/bootstrap.py
$env:PYTHONPATH = "$pwd/apps/api"
python -m uvicorn vocalmorph.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

Open http://localhost:3000. API binding is loopback only; this development API has no authentication and is not intended for public internet exposure.

## VST3

The `VocalMorph Windows` GitHub Actions workflow builds with Visual Studio 2022, tests the plugin and core, bundles the inference runtime, and uploads `VocalMorph-Windows-x64-VST3`. Version tags create releases after all tests pass. See [installation](docs/INSTALL.md), [model packages](docs/MODELS.md), [architecture](docs/ARCHITECTURE.md), and [third-party licenses](docs/THIRD_PARTY.md).
