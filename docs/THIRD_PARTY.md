# Third-party components

- JUCE 8.0.12, commit `29396c22c93392d6738e021b83196283d6e4d850`: AGPLv3/commercial dual license. This repository's original code is AGPL-3.0-only. A proprietary distribution requires appropriate JUCE licensing and an alternative license from all relevant original-code copyright owners.
- RVC source, commit `81eed5e8f68b6bed1789f682fe78cdd324495afc`: MIT. Its LICENSE is included in the runtime. Original RVC authors retain copyright.\n- RVC support weights from `lj1995/VoiceConversionWebUI` (repository license: MIT): RMVPE `rmvpe.pt` pinned at revision `0658a97f086c16951f55b4349c0b25503b6ffdba`, SHA-256 `6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193`; HuBERT/ContentVec pinned at revision `1be9d36ece685661920e1a7cb36eb0437c1e5581`, `pytorch_model.bin` SHA-256 `cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5`. RMVPE's upstream implementation is Apache-2.0.
- PyTorch: BSD-style. Transformers: Apache-2.0. Python: PSF. NumPy/SciPy: BSD. librosa: ISC. SoundFile: BSD. Included dependency license files remain in their distribution metadata.
- Next.js, React, Tailwind and WaveSurfer.js retain their respective open-source licenses; see installed dependency metadata.
- VST3 technology by Steinberg; JUCE bundles the relevant SDK notices.

No Antares code, branding, artwork, assets, models, or celebrity voice resources are distributed. Supplied reference images are not copied into this project.

Voice-model licensing is independent of architecture licensing. Every imported asset must identify its own license and SHA-256 checksum; a consent declaration is an attestation, not verification of legal rights.
