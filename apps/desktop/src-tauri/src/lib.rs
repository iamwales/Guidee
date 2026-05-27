mod commands;
mod hotkeys;
mod tray;

use commands::audio::AudioState;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            let handle = app.handle().clone();
            tray::setup_tray(&handle)?;
            hotkeys::register_hotkeys(&handle)?;

            app.manage(AudioState::new(handle.clone()));

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::screen::capture_screen,
            commands::audio::start_listening,
            commands::audio::stop_listening,
            commands::overlay::show_overlay,
            commands::overlay::hide_overlay,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Guidee");
}
