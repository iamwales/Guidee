use base64::{engine::general_purpose::STANDARD, Engine};
use image::codecs::jpeg::JpegEncoder;
use serde::{Deserialize, Serialize};
use std::io::Cursor;

const DEFAULT_MAX_WIDTH: u32 = 1600;
const DEFAULT_MAX_HEIGHT: u32 = 1000;
const DEFAULT_JPEG_QUALITY: u8 = 72;
const MIN_JPEG_QUALITY: u8 = 45;
const MAX_IMAGE_BYTES: usize = 700_000;

#[tauri::command]
pub async fn list_monitors() -> Result<Vec<MonitorInfo>, String> {
    let monitors = xcap::Monitor::all().map_err(|e| e.to_string())?;
    monitors
        .into_iter()
        .map(|monitor| {
            Ok(MonitorInfo {
                id: monitor.id().map_err(|e| e.to_string())?,
                name: monitor.name().map_err(|e| e.to_string()).ok(),
                friendly_name: monitor.friendly_name().map_err(|e| e.to_string()).ok(),
                x: monitor.x().map_err(|e| e.to_string()).ok(),
                y: monitor.y().map_err(|e| e.to_string()).ok(),
                width: monitor.width().map_err(|e| e.to_string())?,
                height: monitor.height().map_err(|e| e.to_string())?,
                scale_factor: monitor
                    .scale_factor()
                    .map(f64::from)
                    .map_err(|e| e.to_string())
                    .ok(),
                is_primary: monitor.is_primary().map_err(|e| e.to_string()).ok(),
            })
        })
        .collect()
}

#[tauri::command]
pub async fn capture_screen(options: Option<CaptureOptions>) -> Result<ScreenCapture, String> {
    let options = options.unwrap_or_default();
    let source = options.source.unwrap_or_default();

    if matches!(source, CaptureSource::FocusedWindow) {
        if let Ok(capture) = capture_focused_window(&options) {
            return Ok(capture);
        }
    }

    let monitor = if matches!(source, CaptureSource::CursorMonitor) {
        if let (Some(x), Some(y)) = (options.cursor_x, options.cursor_y) {
            xcap::Monitor::from_point(x, y).map_err(|e| e.to_string())?
        } else {
            select_monitor(options.monitor_id)?
        }
    } else {
        select_monitor(options.monitor_id)?
    };

    let image = monitor.capture_image().map_err(|e| e.to_string())?;
    let monitor_id = monitor.id().map_err(|e| e.to_string()).ok();
    let monitor_name = monitor
        .friendly_name()
        .or_else(|_| monitor.name())
        .map_err(|e| e.to_string())
        .ok();

    encode_capture(
        image,
        if matches!(source, CaptureSource::CursorMonitor) {
            CaptureSource::CursorMonitor
        } else {
            CaptureSource::SelectedMonitor
        },
        monitor_id,
        monitor_name,
        options,
    )
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CaptureOptions {
    pub monitor_id: Option<u32>,
    pub source: Option<CaptureSource>,
    pub cursor_x: Option<i32>,
    pub cursor_y: Option<i32>,
    pub max_width: Option<u32>,
    pub max_height: Option<u32>,
    pub quality: Option<u8>,
}

impl Default for CaptureOptions {
    fn default() -> Self {
        Self {
            monitor_id: None,
            source: Some(CaptureSource::SelectedMonitor),
            cursor_x: None,
            cursor_y: None,
            max_width: Some(DEFAULT_MAX_WIDTH),
            max_height: Some(DEFAULT_MAX_HEIGHT),
            quality: Some(DEFAULT_JPEG_QUALITY),
        }
    }
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum CaptureSource {
    SelectedMonitor,
    FocusedWindow,
    CursorMonitor,
}

impl Default for CaptureSource {
    fn default() -> Self {
        Self::SelectedMonitor
    }
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MonitorInfo {
    pub id: u32,
    pub name: Option<String>,
    pub friendly_name: Option<String>,
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub width: u32,
    pub height: u32,
    pub scale_factor: Option<f64>,
    pub is_primary: Option<bool>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ScreenCapture {
    pub image_b64: String,
    pub media_type: &'static str,
    pub source: CaptureSource,
    pub monitor_id: Option<u32>,
    pub monitor_name: Option<String>,
    pub width: u32,
    pub height: u32,
    pub original_width: u32,
    pub original_height: u32,
    pub quality: u8,
    pub byte_size: usize,
}

fn select_monitor(monitor_id: Option<u32>) -> Result<xcap::Monitor, String> {
    let monitors = xcap::Monitor::all().map_err(|e| e.to_string())?;

    if let Some(id) = monitor_id {
        monitors
            .into_iter()
            .find(|monitor| monitor.id().ok() == Some(id))
            .ok_or_else(|| format!("Monitor {id} not found"))
    } else {
        monitors
            .into_iter()
            .next()
            .ok_or("No monitors found".to_string())
    }
}

fn capture_focused_window(options: &CaptureOptions) -> Result<ScreenCapture, String> {
    let windows = xcap::Window::all().map_err(|e| e.to_string())?;
    let window = windows
        .into_iter()
        .find(|window| {
            window.is_focused().unwrap_or(false) && !window.is_minimized().unwrap_or(true)
        })
        .ok_or_else(|| "No focused window found".to_string())?;

    let monitor = window.current_monitor().ok();
    let monitor_id = monitor.as_ref().and_then(|monitor| monitor.id().ok());
    let monitor_name = monitor
        .as_ref()
        .and_then(|monitor| monitor.friendly_name().or_else(|_| monitor.name()).ok());

    encode_capture(
        window.capture_image().map_err(|e| e.to_string())?,
        CaptureSource::FocusedWindow,
        monitor_id,
        monitor_name,
        options.clone(),
    )
}

fn encode_capture(
    rgba: image::RgbaImage,
    source: CaptureSource,
    monitor_id: Option<u32>,
    monitor_name: Option<String>,
    options: CaptureOptions,
) -> Result<ScreenCapture, String> {
    let (w, h) = rgba.dimensions();
    let max_width = options.max_width.unwrap_or(DEFAULT_MAX_WIDTH).max(1);
    let max_height = options.max_height.unwrap_or(DEFAULT_MAX_HEIGHT).max(1);
    let (nw, nh) = scale_dimensions(w, h, max_width, max_height);

    let resized = if nw != w || nh != h {
        image::imageops::resize(&rgba, nw, nh, image::imageops::FilterType::Lanczos3)
    } else {
        rgba
    };
    let rgb = image::DynamicImage::ImageRgba8(resized).to_rgb8();
    let requested_quality = options
        .quality
        .unwrap_or(DEFAULT_JPEG_QUALITY)
        .clamp(MIN_JPEG_QUALITY, 95);
    let (bytes, quality) = encode_jpeg(&rgb, requested_quality)?;

    Ok(ScreenCapture {
        image_b64: STANDARD.encode(&bytes),
        media_type: "image/jpeg",
        source,
        monitor_id,
        monitor_name,
        width: rgb.width(),
        height: rgb.height(),
        original_width: w,
        original_height: h,
        quality,
        byte_size: bytes.len(),
    })
}

fn encode_jpeg(rgb: &image::RgbImage, requested_quality: u8) -> Result<(Vec<u8>, u8), String> {
    let mut quality = requested_quality;
    loop {
        let mut buf = Cursor::new(Vec::new());
        let mut encoder = JpegEncoder::new_with_quality(&mut buf, quality);
        encoder
            .encode(
                rgb.as_raw(),
                rgb.width(),
                rgb.height(),
                image::ExtendedColorType::Rgb8,
            )
            .map_err(|e| e.to_string())?;

        let bytes = buf.into_inner();
        if bytes.len() <= MAX_IMAGE_BYTES || quality <= MIN_JPEG_QUALITY {
            return Ok((bytes, quality));
        }
        quality = quality.saturating_sub(8).max(MIN_JPEG_QUALITY);
    }
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
