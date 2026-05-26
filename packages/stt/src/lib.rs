//! Local speech-to-text via Whisper.cpp (whisper-rs).
//!
//! Download a model to `models/whisper-base.en.bin` and enable the
//! `whisper-rs` feature when ready for production transcription.

#[derive(Debug, Clone)]
pub struct SttConfig {
    pub model_path: String,
    pub language: Option<String>,
}

impl Default for SttConfig {
    fn default() -> Self {
        Self {
            model_path: "models/whisper-base.en.bin".into(),
            language: Some("en".into()),
        }
    }
}

pub struct WhisperEngine {
    config: SttConfig,
}

impl WhisperEngine {
    pub fn new(config: SttConfig) -> Self {
        Self { config }
    }

    /// Transcribe 16-bit PCM audio (16 kHz mono).
    pub fn transcribe(&self, _pcm: &[i16]) -> Result<String, String> {
        let _ = &self.config;
        Ok(String::new())
    }
}
