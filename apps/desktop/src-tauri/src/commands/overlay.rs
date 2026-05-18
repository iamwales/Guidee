use tauri::{AppHandle, LogicalPosition, Manager};

#[tauri::command]
pub async fn show_overlay(app: AppHandle, x: f64, y: f64) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or("Main window not found")?;
    window
        .set_position(LogicalPosition::new(x + 20.0, y + 20.0))
        .map_err(|e| e.to_string())?;
    window.show().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub async fn hide_overlay(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}
