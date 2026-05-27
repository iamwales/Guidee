This directory vendors the minimal Picovoice Porcupine native SDK assets needed
by `guidee-wake-word`.

Source: https://github.com/Picovoice/porcupine
License: see `LICENSE` in this directory.

Bundled assets:
- C headers: `include/picovoice.h`, `include/pv_porcupine.h`
- Native libraries for macOS arm64, macOS x86_64, Linux x86_64,
  Windows x86_64, and Windows arm64
- English Porcupine model: `lib/common/porcupine_params.pv`
- Built-in `picovoice` keyword files for macOS, Linux, and Windows

Runtime use requires a Picovoice AccessKey from https://console.picovoice.ai/.
