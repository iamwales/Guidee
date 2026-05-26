//! On-device wake word detection (Picovoice Porcupine).
//!
//! Wire `pv_porcupine` when `PICOVOICE_ACCESS_KEY` is set.
//! Until then, exposes a stub that always returns false.

#[derive(Debug, Clone)]
pub struct WakeWordConfig {
    pub keyword: String,
    pub sensitivity: f32,
}

impl Default for WakeWordConfig {
    fn default() -> Self {
        Self {
            keyword: "guidee".into(),
            sensitivity: 0.5,
        }
    }
}

pub struct WakeWordEngine {
    config: WakeWordConfig,
}

impl WakeWordEngine {
    pub fn new(config: WakeWordConfig) -> Self {
        Self { config }
    }

    /// Process a PCM frame (16-bit LE mono). Returns true if wake word detected.
    pub fn process_frame(&mut self, _pcm: &[i16]) -> bool {
        // TODO: Porcupine integration
        let _ = &self.config;
        false
    }
}
