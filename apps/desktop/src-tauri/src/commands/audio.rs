use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use guidee_stt::{SttConfig, WhisperEngine};
use guidee_wake_word::{WakeWordConfig, WakeWordEngine};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, State};

const TARGET_SAMPLE_RATE: u32 = 16_000;
const FRAME_MS: u64 = 100;
const SILENCE_END_MS: u64 = 900;
const MIN_SPEECH_MS: u64 = 300;
const MAX_UTTERANCE_MS: u64 = 15_000;
const RMS_SPEECH_THRESHOLD: f32 = 0.015;

pub struct AudioState {
    pub app: AppHandle,
    session: Mutex<Option<VoiceSession>>,
}

impl AudioState {
    pub fn new(app: AppHandle) -> Self {
        Self {
            app,
            session: Mutex::new(None),
        }
    }
}

struct VoiceSession {
    stop_tx: mpsc::Sender<()>,
    _worker: thread::JoinHandle<()>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VoiceOptions {
    model_path: Option<String>,
    language: Option<String>,
    wake_word_enabled: Option<bool>,
    wake_word_sensitivity: Option<f32>,
    picovoice_access_key: Option<String>,
    wake_word_model_path: Option<String>,
    wake_word_keyword_path: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct VoiceStatusPayload {
    state: &'static str,
    detail: Option<String>,
}

#[tauri::command]
pub async fn start_listening(
    app: AppHandle,
    state: State<'_, AudioState>,
    options: Option<VoiceOptions>,
) -> Result<(), String> {
    let state = state.inner();
    if state.session.lock().is_some() {
        return Ok(());
    }

    let options = options.unwrap_or(VoiceOptions {
        model_path: None,
        language: None,
        wake_word_enabled: None,
        wake_word_sensitivity: None,
        picovoice_access_key: None,
        wake_word_model_path: None,
        wake_word_keyword_path: None,
    });
    let (stop_tx, stop_rx) = mpsc::channel::<()>();
    let (ready_tx, ready_rx) = mpsc::channel::<Result<(), String>>();
    let worker_app = state.app.clone();
    let worker = thread::spawn(move || {
        run_voice_worker(worker_app, stop_rx, ready_tx, options);
    });

    match ready_rx.recv_timeout(Duration::from_secs(5)) {
        Ok(Ok(())) => {}
        Ok(Err(err)) => return Err(err),
        Err(_) => return Err("Microphone setup timed out".into()),
    }

    *state.session.lock() = Some(VoiceSession {
        stop_tx,
        _worker: worker,
    });

    let _ = app;
    Ok(())
}

#[tauri::command]
pub async fn stop_listening(state: State<'_, AudioState>) -> Result<(), String> {
    let state = state.inner();
    if let Some(session) = state.session.lock().take() {
        let _ = session.stop_tx.send(());
    }
    emit_status(&state.app, "idle", Some("Microphone stream stopped"));
    Ok(())
}

fn build_input_stream_f32(
    device: &cpal::Device,
    config: &cpal::StreamConfig,
    channels: usize,
    audio_tx: mpsc::Sender<Vec<i16>>,
    app: AppHandle,
) -> Result<cpal::Stream, String> {
    device
        .build_input_stream(
            config,
            move |data: &[f32], _| {
                let _ = audio_tx.send(mono_from_f32(data, channels));
            },
            move |err| emit_error(&app, format!("Microphone stream error: {err}")),
            None,
        )
        .map_err(|err| format!("Unable to build microphone stream: {err}"))
}

fn build_input_stream_i16(
    device: &cpal::Device,
    config: &cpal::StreamConfig,
    channels: usize,
    audio_tx: mpsc::Sender<Vec<i16>>,
    app: AppHandle,
) -> Result<cpal::Stream, String> {
    device
        .build_input_stream(
            config,
            move |data: &[i16], _| {
                let _ = audio_tx.send(mono_from_i16(data, channels));
            },
            move |err| emit_error(&app, format!("Microphone stream error: {err}")),
            None,
        )
        .map_err(|err| format!("Unable to build microphone stream: {err}"))
}

fn build_input_stream_u16(
    device: &cpal::Device,
    config: &cpal::StreamConfig,
    channels: usize,
    audio_tx: mpsc::Sender<Vec<i16>>,
    app: AppHandle,
) -> Result<cpal::Stream, String> {
    device
        .build_input_stream(
            config,
            move |data: &[u16], _| {
                let _ = audio_tx.send(mono_from_u16(data, channels));
            },
            move |err| emit_error(&app, format!("Microphone stream error: {err}")),
            None,
        )
        .map_err(|err| format!("Unable to build microphone stream: {err}"))
}

fn run_voice_worker(
    app: AppHandle,
    stop_rx: mpsc::Receiver<()>,
    ready_tx: mpsc::Sender<Result<(), String>>,
    options: VoiceOptions,
) {
    let host = cpal::default_host();
    let Some(device) = host.default_input_device() else {
        let _ = ready_tx.send(Err("No input microphone was found".into()));
        return;
    };
    let config = match device.default_input_config() {
        Ok(config) => config,
        Err(err) => {
            let _ = ready_tx.send(Err(format!("Unable to read microphone config: {err}")));
            return;
        }
    };
    let sample_rate = config.sample_rate().0;
    let channels = usize::from(config.channels());
    let stream_config = config.config();
    let (audio_tx, audio_rx) = mpsc::channel::<Vec<i16>>();
    let error_app = app.clone();
    let stream = match config.sample_format() {
        cpal::SampleFormat::F32 => {
            build_input_stream_f32(&device, &stream_config, channels, audio_tx, error_app)
        }
        cpal::SampleFormat::I16 => {
            build_input_stream_i16(&device, &stream_config, channels, audio_tx, error_app)
        }
        cpal::SampleFormat::U16 => {
            build_input_stream_u16(&device, &stream_config, channels, audio_tx, error_app)
        }
        sample_format => Err(format!(
            "Unsupported microphone sample format: {sample_format:?}"
        )),
    };
    let stream = match stream {
        Ok(stream) => stream,
        Err(err) => {
            let _ = ready_tx.send(Err(err));
            return;
        }
    };
    if let Err(err) = stream.play() {
        let _ = ready_tx.send(Err(format!("Unable to start microphone stream: {err}")));
        return;
    }
    let _stream = stream;
    emit_status(&app, "listening", Some("Microphone stream started"));
    let _ = ready_tx.send(Ok(()));

    let stt_config = SttConfig {
        model_path: options
            .model_path
            .filter(|path| !path.trim().is_empty())
            .unwrap_or_else(|| SttConfig::default().model_path),
        language: options.language.or_else(|| SttConfig::default().language),
    };
    let stt = WhisperEngine::new(stt_config);
    if let Err(err) = &stt {
        emit_error(&app, err.to_string());
    }

    let wake_word_enabled = options.wake_word_enabled.unwrap_or(false);
    let mut wake_word = if wake_word_enabled {
        match WakeWordEngine::new(WakeWordConfig {
            sensitivity: options.wake_word_sensitivity.unwrap_or(0.5),
            access_key: options
                .picovoice_access_key
                .filter(|key| !key.trim().is_empty())
                .or_else(|| WakeWordConfig::default().access_key),
            model_path: options
                .wake_word_model_path
                .filter(|path| !path.trim().is_empty()),
            keyword_path: options
                .wake_word_keyword_path
                .filter(|path| !path.trim().is_empty()),
            ..WakeWordConfig::default()
        }) {
            Ok(engine) => {
                emit_status(
                    &app,
                    "waitingWake",
                    Some(&format!("Waiting for '{}'", engine.keyword())),
                );
                Some(engine)
            }
            Err(err) => {
                emit_error(&app, format!("Wake word unavailable: {err}"));
                Some(WakeWordEngine::disabled(WakeWordConfig::default()))
            }
        }
    } else {
        None
    };

    let mut utterance = Vec::new();
    let mut active = false;
    let mut wake_detected = wake_word
        .as_ref()
        .map(|engine| !engine.is_configured())
        .unwrap_or(true);
    let mut speech_started = Instant::now();
    let mut last_voice = Instant::now();

    loop {
        if stop_rx.try_recv().is_ok() {
            break;
        }

        let chunk = match audio_rx.recv_timeout(Duration::from_millis(FRAME_MS)) {
            Ok(chunk) => chunk,
            Err(mpsc::RecvTimeoutError::Timeout) => continue,
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
        };

        if let Some(engine) = wake_word.as_mut() {
            let wake_chunk = resample_to_16khz(&chunk, sample_rate);
            match engine.process_frame(&wake_chunk) {
                Ok(true) => {
                    wake_detected = true;
                    emit_status(&app, "listening", Some("Wake word detected"));
                }
                Ok(false) => {}
                Err(err) => {
                    wake_detected = true;
                    emit_error(&app, format!("Wake word failed: {err}"));
                }
            }
        }

        let now = Instant::now();
        let voiced = rms(&chunk) >= RMS_SPEECH_THRESHOLD;
        if !wake_detected {
            continue;
        }
        if voiced {
            if !active {
                active = true;
                speech_started = now;
                utterance.clear();
                emit_status(&app, "recording", Some("Speech detected"));
            }
            last_voice = now;
        }

        if active {
            utterance.extend_from_slice(&chunk);
            let silence_elapsed = now.duration_since(last_voice);
            let utterance_elapsed = now.duration_since(speech_started);
            let should_finish = silence_elapsed >= Duration::from_millis(SILENCE_END_MS)
                || utterance_elapsed >= Duration::from_millis(MAX_UTTERANCE_MS);

            if should_finish {
                if utterance_elapsed >= Duration::from_millis(MIN_SPEECH_MS) {
                    transcribe_utterance(&app, &stt, &utterance, sample_rate);
                }
                utterance.clear();
                active = false;
                wake_detected = wake_word
                    .as_ref()
                    .map(|engine| !engine.is_configured())
                    .unwrap_or(true);
                emit_status(
                    &app,
                    if wake_detected {
                        "listening"
                    } else {
                        "waitingWake"
                    },
                    Some(if wake_detected {
                        "Waiting for speech"
                    } else {
                        "Waiting for wake word"
                    }),
                );
            }
        }
    }

    emit_status(&app, "idle", Some("Microphone worker stopped"));
}

fn transcribe_utterance(
    app: &AppHandle,
    stt: &Result<WhisperEngine, guidee_stt::SttError>,
    utterance: &[i16],
    sample_rate: u32,
) {
    let Ok(engine) = stt else {
        return;
    };
    let pcm = resample_to_16khz(utterance, sample_rate);
    match engine.transcribe(&pcm) {
        Ok(text) if !text.trim().is_empty() => {
            let _ = app.emit("transcription-ready", text.trim());
        }
        Ok(_) => {}
        Err(err) => emit_error(app, err.to_string()),
    }
}

fn mono_from_f32(data: &[f32], channels: usize) -> Vec<i16> {
    data.chunks(channels)
        .map(|frame| {
            let mixed = frame.iter().copied().sum::<f32>() / channels as f32;
            (mixed.clamp(-1.0, 1.0) * f32::from(i16::MAX)) as i16
        })
        .collect()
}

fn mono_from_i16(data: &[i16], channels: usize) -> Vec<i16> {
    data.chunks(channels)
        .map(|frame| {
            let mixed =
                frame.iter().map(|sample| i32::from(*sample)).sum::<i32>() / channels as i32;
            mixed.clamp(i32::from(i16::MIN), i32::from(i16::MAX)) as i16
        })
        .collect()
}

fn mono_from_u16(data: &[u16], channels: usize) -> Vec<i16> {
    data.chunks(channels)
        .map(|frame| {
            let mixed =
                frame.iter().map(|sample| i32::from(*sample)).sum::<i32>() / channels as i32;
            (mixed - 32_768).clamp(i32::from(i16::MIN), i32::from(i16::MAX)) as i16
        })
        .collect()
}

fn rms(samples: &[i16]) -> f32 {
    if samples.is_empty() {
        return 0.0;
    }
    let sum = samples
        .iter()
        .map(|sample| {
            let normalized = f32::from(*sample) / f32::from(i16::MAX);
            normalized * normalized
        })
        .sum::<f32>();
    (sum / samples.len() as f32).sqrt()
}

fn resample_to_16khz(samples: &[i16], sample_rate: u32) -> Vec<i16> {
    if sample_rate == TARGET_SAMPLE_RATE || samples.is_empty() {
        return samples.to_vec();
    }
    let ratio = sample_rate as f32 / TARGET_SAMPLE_RATE as f32;
    let target_len = (samples.len() as f32 / ratio).ceil() as usize;
    (0..target_len)
        .filter_map(|index| {
            samples
                .get((index as f32 * ratio).floor() as usize)
                .copied()
        })
        .collect()
}

fn emit_status(app: &AppHandle, state: &'static str, detail: Option<&str>) {
    let _ = app.emit(
        "voice-status",
        VoiceStatusPayload {
            state,
            detail: detail.map(str::to_string),
        },
    );
}

fn emit_error(app: &AppHandle, message: String) {
    let _ = app.emit("voice-error", message);
}
