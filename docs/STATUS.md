# Development status

Implemented: original Next.js studio; audio import/record/pause/stop/replay; WaveSurfer display and seek; model filtering/favorites/recent; model package import/delete and metadata; factory/custom presets with JSON import/export; async transform API, cache and WAV export; shared C++ DSP and C ABI; native JUCE VST3; state/automation parameters; sample-rate handling, mono/stereo, bypass, denormal protection; bounded audio queues and timestamped worker output; bundled local PyTorch/RVC runtime; .pth + HuBERT + RMVPE inference code; Windows build/package/release workflows.

No trained voice, HuBERT or RMVPE weights are included. A valid authorized package is required for neural processing. No celebrity or downloadable voice catalog is fabricated. End-to-end neural quality and realtime throughput have not been validated with trained weights.

Known product gaps: no standalone native offline file editor, no native model search/catalog/cache UI, no cross-platform preset format between native XML and web JSON, no retrieval-index blending, no independent true formant shifter, no musical scale selector, no GPU acceleration, no neural SOLA, no neural output queue catch-up. Chromatic tune controls are neural-only. Native 640 ms live mode is experimental and is not suitable for low-latency stage monitoring. DAW accelerated offline neural rendering is unsupported. A/B web audition restarts the chosen clip; it is not sample-synchronous switching. Long offline neural windows use contextual trimming without overlap-add.

Checksums verify file integrity, not publisher identity. Metadata is an attestation of rights. Imported models should be trusted. The loopback development API has no authentication and must not be published directly.
