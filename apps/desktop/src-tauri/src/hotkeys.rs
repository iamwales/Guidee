use tauri::{AppHandle, Emitter};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

pub fn register_hotkeys(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let gs = app.global_shortcut();

    let toggle = Shortcut::new(Some(Modifiers::SUPER | Modifiers::SHIFT), Code::KeyG);
    let capture = Shortcut::new(Some(Modifiers::SUPER | Modifiers::SHIFT), Code::KeyS);
    let escape = Shortcut::new(None, Code::Escape);

    gs.register(toggle)?;
    gs.register(capture)?;
    gs.register(escape)?;

    let app_toggle = app.clone();
    gs.on_shortcut(toggle, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            let _ = app_toggle.emit("toggle-overlay", ());
        }
    })?;

    let app_capture = app.clone();
    gs.on_shortcut(capture, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            let _ = app_capture.emit("capture-and-ask", ());
        }
    })?;

    let app_escape = app.clone();
    gs.on_shortcut(escape, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            let _ = app_escape.emit("dismiss-overlay", ());
        }
    })?;

    Ok(())
}
