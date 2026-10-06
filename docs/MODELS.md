# Custom .pth models and RMVPE

VocalMorph VST3 loads an authorized RVC v1/v2 F0 checkpoint directly from a `.pth` file. A `manifest.json` is **not required** for direct VST model loading.

Supported checkpoints: RVC v1 (256 features) and v2 (768 features), F0-enabled inference checkpoints, 32/40/48 kHz, speaker 0. Training checkpoints, arbitrary PyTorch architectures, and non-F0 checkpoints are rejected.

## RMVPE + HuBERT are bundled

The full Windows artifact now contains the common support models used by RVC:

```
VocalMorph.vst3/
  Contents/
    Resources/
      assets/
        rmvpe/
          rmvpe.pt
        hubert_base/
          config.json
          preprocessor_config.json
          pytorch_model.bin
```

These shared assets are downloaded from the RVC-recommended `lj1995/VoiceConversionWebUI` model repository during the GitHub Actions build. The large binaries are pinned/checksum-verified. You therefore only need to select your authorized voice `.pth` in the plugin.

For compatibility with custom installations, VocalMorph can also use the older side-by-side layout (`rmvpe.pt` plus `hubert/`). Asset validation now happens before expensive PyTorch/RVC initialization, so a broken package fails immediately instead of appearing stuck on model loading.

When a `.pth` is selected, VocalMorph safely inspects the checkpoint with PyTorch `weights_only=True`, detects RVC v1/v2 and the checkpoint sample rate, validates architecture/resource limits, then loads it in the separate worker process.

Only use voice checkpoints you have permission to use.
