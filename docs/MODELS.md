# Custom .pth models and RMVPE

VocalMorph VST3 can load an authorized RVC v1/v2 F0 checkpoint directly from a `.pth` file. A `manifest.json` is **not required** for direct VST model loading.

Supported checkpoints: RVC v1 (256 features) and v2 (768 features), F0-enabled inference checkpoints, 32/40/48 kHz, speaker 0. Training checkpoints, arbitrary PyTorch architectures, and non-F0 checkpoints are rejected.

The voice checkpoint is only one part of inference. VocalMorph also needs RMVPE and a compatible local HuBERT/ContentVec encoder. Put these assets either beside the selected `.pth`:

```
MyVoice.pth
rmvpe.pt
hubert/
  config.json
  preprocessor_config.json
  model.safetensors
```

or install the common support assets in the plugin's `Contents/Resources/assets` directory. The same RMVPE/HuBERT assets can then be reused by multiple `.pth` voice models.

When a `.pth` is selected, VocalMorph safely inspects the checkpoint with PyTorch `weights_only=True`, detects RVC v1/v2 and the checkpoint sample rate, validates architecture/resource limits, then loads it in the separate worker process. The model does not need JSON metadata.

The web Model Manager may still use the stricter packaged-model format for catalog/import workflows, where provenance, checksums, consent and licensing metadata are useful. That package format is separate from direct VST `.pth` loading.

Only use voice checkpoints and support weights that you have permission to use.
