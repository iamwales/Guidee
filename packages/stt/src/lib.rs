//! Local speech-to-text via Whisper.cpp (`whisper-rs`).
//!
//! Download a ggml model to `models/whisper-base.en.bin` and enable the
//! `whisper` feature for production transcription.

use std::path::Path;

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

#[derive(Debug, Clone)]
pub enum SttError {
    ModelMissing(String),
    EngineUnavailable,
    TranscriptionFailed(String),
}

impl std::fmt::Display for SttError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ModelMissing(path) => write!(f, "Whisper model not found at {path}"),
            Self::EngineUnavailable => write!(f, "Whisper support is not enabled in this build"),
            Self::TranscriptionFailed(message) => write!(f, "{message}"),
        }
    }
}

impl std::error::Error for SttError {}

pub struct WhisperEngine {
    config: SttConfig,
    #[cfg(feature = "whisper")]
    context: whisper_rs::WhisperContext,
}

impl WhisperEngine {
    pub fn new(config: SttConfig) -> Result<Self, SttError> {
        if !Path::new(&config.model_path).exists() {
            return Err(SttError::ModelMissing(config.model_path));
        }

        #[cfg(feature = "whisper")]
        {
            let context = whisper_rs::WhisperContext::new_with_params(
                &config.model_path,
                whisper_rs::WhisperContextParameters::default(),
            )
            .map_err(|err| SttError::TranscriptionFailed(err.to_string()))?;
            Ok(Self { config, context })
        }

        #[cfg(not(feature = "whisper"))]
        {
            let _ = &config;
            Err(SttError::EngineUnavailable)
        }
    }

    /// Transcribe 16-bit PCM audio (16 kHz mono).
    pub fn transcribe(&self, pcm: &[i16]) -> Result<String, SttError> {
        if pcm.is_empty() {
            return Ok(String::new());
        }

        #[cfg(feature = "whisper")]
        {
            let mut state = self
                .context
                .create_state()
                .map_err(|err| SttError::TranscriptionFailed(err.to_string()))?;
            let mut params =
                whisper_rs::FullParams::new(whisper_rs::SamplingStrategy::Greedy { best_of: 1 });
            params.set_language(self.config.language.as_deref());
            params.set_print_special(false);
            params.set_print_progress(false);
            params.set_print_realtime(false);
            params.set_print_timestamps(false);

            let samples = pcm_to_f32(pcm);
            state
                .full(params, &samples)
                .map_err(|err| SttError::TranscriptionFailed(err.to_string()))?;

            let text = state
                .as_iter()
                .map(|segment| segment.to_string())
                .collect::<Vec<_>>()
                .join(" ")
                .trim()
                .to_string();
            Ok(text)
        }

        #[cfg(not(feature = "whisper"))]
        {
            let _ = &self.config;
            let _ = pcm;
            Err(SttError::EngineUnavailable)
        }
    }
}

pub fn pcm_to_f32(pcm: &[i16]) -> Vec<f32> {
    pcm.iter()
        .map(|sample| f32::from(*sample) / f32::from(i16::MAX))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn converts_pcm_to_normalized_f32() {
        let samples = pcm_to_f32(&[0, i16::MAX, i16::MIN]);
        assert_eq!(samples[0], 0.0);
        assert!(samples[1] > 0.99);
        assert!(samples[2] < -0.99);
    }

    #[test]
    fn reports_missing_model() {
        let result = WhisperEngine::new(SttConfig {
            model_path: "/missing/model.bin".into(),
            language: Some("en".into()),
        });

        assert!(matches!(result, Err(SttError::ModelMissing(_))));
    }
}
