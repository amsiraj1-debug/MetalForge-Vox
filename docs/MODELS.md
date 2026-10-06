# Custom .pth models and RMVPE

Supported: RVC v1 (256 features) and v2 (768 features), F0-enabled inference checkpoints, 32/40/48 kHz, speaker 0. RMVPE estimates pitch; HuBERT/ContentVec encodes content; the .pth synthesizer converts the voice. Training checkpoints, arbitrary PyTorch architectures, non-F0 checkpoints and external Python code are rejected.

Create a directory with `manifest.json`, `model.pth`, `rmvpe.pt`, and `hubert/{config.json,preprocessor_config.json,model.safetensors}`. HuBERT must be a compatible locally converted RVC ContentVec/HuBERT checkpoint; v1 needs its trained final projection. Do not substitute an unrelated encoder.

Copy models/manifests/custom.example.json to manifest.json, fill the actual metadata and each asset's license, and run `python tools/package_model.py YOUR_FOLDER --output my-voice.zip`. The helper fills checksums. Upload the ZIP in the web Model Manager. In the VST3 choose the .pth or manifest in the **unpacked** directory. No background model downloads occur.

The loader forces PyTorch weights-only deserialization, requires safetensors for the encoder, checks paths, architecture, file hashes and resource limits, and loads weights in a separate process. These measures reduce risk; they are not a sandbox for malicious native-library exploits. Only install trusted, authorized packages.

No licensed model weights were supplied for this build. Neural speech quality, base-model compatibility and live CPU performance require validation with actual authorized packages. The tests do not claim to evaluate voice similarity.
