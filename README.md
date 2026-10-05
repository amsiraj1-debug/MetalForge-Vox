# MetalForge Vox

Self-contained Windows VST3 builder for RVC voice conversion.

## What this repository does

This repository builds a Windows x64 VST3 based on the official RVC Realtime VST architecture, but packages the RVC source/runtime with the plugin so the user does not have to manually start RVC WebUI, OpenVoice, or a separate Python server.

The plugin supports:

- Direct RVC `.pth` model selection
- Optional `.index` selection
- RMVPE / FCPE / PM F0 methods
- Pitch, formant, retrieval/index rate, RMS mix, gate, block, crossfade, context, dry/wet, and output controls
- Automatic launch of the bundled worker
- Shared-memory audio transport between the VST and the bundled inference worker
- Windows VST3 build through GitHub Actions

## Build

Open the **Actions** tab and run **Build MetalForge Vox VST3**.

The workflow pins the upstream RVC project to:

`81eed5e8f68b6bed1789f682fe78cdd324495afc`

It builds the VST3, patches it for the MetalForge Vox name and bundled-runtime defaults, packages a portable Python runtime plus RVC inference source, and uploads a ZIP artifact.

## Runtime profiles

The default workflow packages the **CPU** runtime because it is the most portable. A CUDA runtime is much larger and should be added as a separate release profile once the CPU artifact is building reliably.

## Model files

User voice models are not included. Load a model you own or have permission to use:

- `Voice.pth`
- optional `Voice.index`

## Important

RVC `.pth` checkpoints are PyTorch checkpoints, so a direct raw-`.pth` VST requires the RVC/PyTorch inference runtime. This project bundles that runtime with the plugin package rather than requiring the user to start it manually.

Third-party components retain their original licenses. Review the RVC, iPlug2, Steinberg VST3 SDK, Python, PyTorch, Transformers, FAISS and model licenses before redistribution.
