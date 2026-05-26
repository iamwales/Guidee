use base64::{engine::general_purpose::STANDARD, Engine};
use image::codecs::jpeg::JpegEncoder;
use std::io::Cursor;

const MAX_WIDTH: u32 = 1920;
const MAX_HEIGHT: u32 = 1080;
const JPEG_QUALITY: u8 = 75;

#[tauri::command]
pub async fn capture_screen(monitor_id: Option<u32>) -> Result<String, String> {
    let monitors = xcap::Monitor::all().map_err(|e| e.to_string())?;

    let monitor = if let Some(id) = monitor_id {
        monitors
            .into_iter()
            .find(|m| m.id().ok() == Some(id))
            .ok_or_else(|| format!("Monitor {id} not found"))?
    } else {
        monitors.into_iter().next().ok_or("No monitors found")?
    };

    let image = monitor.capture_image().map_err(|e| e.to_string())?;
    let rgba = image;
    let (w, h) = rgba.dimensions();

    let (nw, nh) = scale_dimensions(w, h, MAX_WIDTH, MAX_HEIGHT);
    let resized = if nw != w || nh != h {
        image::imageops::resize(&rgba, nw, nh, image::imageops::FilterType::Lanczos3)
    } else {
        rgba
    };

    let mut buf = Cursor::new(Vec::new());
    let mut encoder = JpegEncoder::new_with_quality(&mut buf, JPEG_QUALITY);
    encoder
        .encode(
            resized.as_raw(),
            resized.width(),
            resized.height(),
            image::ExtendedColorType::Rgba8,
        )
        .map_err(|e| e.to_string())?;

    Ok(STANDARD.encode(buf.into_inner()))
}

fn scale_dimensions(w: u32, h: u32, max_w: u32, max_h: u32) -> (u32, u32) {
    if w <= max_w && h <= max_h {
        return (w, h);
    }
    let ratio_w = max_w as f64 / w as f64;
    let ratio_h = max_h as f64 / h as f64;
    let ratio = ratio_w.min(ratio_h);
    (
        (w as f64 * ratio).round() as u32,
        (h as f64 * ratio).round() as u32,
    )
}
