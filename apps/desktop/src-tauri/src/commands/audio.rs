use parking_lot::Mutex;
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};

static LISTENING: Mutex<bool> = Mutex::new(false);

pub struct AudioState {
    pub app: AppHandle,
}

#[tauri::command]
pub async fn start_listening(
    app: AppHandle,
    state: State<'_, Arc<AudioState>>,
) -> Result<(), String> {
    let mut listening = LISTENING.lock();
    if *listening {
        return Ok(());
    }
    *listening = true;
    drop(listening);

    let handle = state.app.clone();
    tauri::async_runtime::spawn(async move {
        // Production: stream mic via cpal → Porcupine wake word → Whisper.cpp
        // Dev stub: simulate transcription after delay
        tokio::time::sleep(std::time::Duration::from_millis(800)).await;
        let _ = handle.emit("transcription-ready", "Hello from voice (stub)");
        *LISTENING.lock() = false;
    });

    let _ = app;
    Ok(())
}

#[tauri::command]
pub async fn stop_listening() -> Result<(), String> {
    *LISTENING.lock() = false;
    Ok(())
}
