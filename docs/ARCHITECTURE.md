# Architecture

The web app talks to a loopback FastAPI service. Uploaded audio is decoded, checked for finite data and duration, converted to mono/48 kHz, optionally normalized, and content-hashed. Transform jobs run in a bounded single-worker process pool. The API event loop does no inference. Cache keys include pipeline version, source hash, complete model metadata/checksums, and canonical parameters. Cache writes use an atomic rename.

The reusable C++ VocalMorphCore implements streaming tone, granular pitch shifting, compression, saturation, transient/consonant-sensitive de-essing, mixing and gain. Its C ABI is used by the Python offline engine, so DSP behavior is shared. Formant is a spectral-color control rather than a true independent formant transposition algorithm.

The shared Python RvcEngine implements weights-only RVC checkpoint loading, local safetensors HuBERT content extraction, RMVPE pitch extraction, chromatic pitch correction and synthesis. The pinned MIT RVC dependency supplies the network architectures. No external server or cloud inference is involved in the packaged VST3.

The JUCE audio callback owns preallocated DSP state and dry-delay storage. It exchanges timestamped mono samples through bounded SPSC queues with a dedicated control/inference thread. That thread starts a bundled Python subprocess and communicates through binary anonymous pipes. Model loading, disk I/O, IPC, tensor work and allocation take place away from the realtime callback. Each instance owns its worker, process and queues. Late output is discarded instead of being played against a later source block; dry audio retains the reported delay on underrun and bypass. Model/sample-rate changes advance a generation identifier.

DSP monitoring reports zero fixed latency. The granular pitch effect has a pitch-dependent short delay. Neural monitoring reports 640 ms, with 160 ms chunks and 320 ms of past context. This prototype does not implement SOLA alignment/crossfades between neural chunks, accelerated host offline inference, GPU providers or sub-100 ms neural monitoring. The native editor is narrower in scope than the web model manager: it loads unpacked packages and native presets; waveform recording/import/export and the cache manager currently live in the web app.

For final production use, offline web conversion uses 8-second chunks with 250 ms context and returns a deterministic cached WAV. A future fully native tensor backend can implement the same engine interface, but no such C++ neural backend is claimed here.
