//! On-device wake word detection via Picovoice Porcupine.
//!
//! Enable the `porcupine` feature to link the vendored native SDK. Runtime use
//! still requires a Picovoice AccessKey.

use std::path::Path;

#[derive(Debug, Clone)]
pub struct WakeWordConfig {
    pub keyword: String,
    pub sensitivity: f32,
    pub access_key: Option<String>,
    pub model_path: Option<String>,
    pub keyword_path: Option<String>,
    pub device: String,
}

impl Default for WakeWordConfig {
    fn default() -> Self {
        Self {
            keyword: "picovoice".into(),
            sensitivity: 0.5,
            access_key: std::env::var("PICOVOICE_ACCESS_KEY").ok(),
            model_path: None,
            keyword_path: None,
            device: "cpu".into(),
        }
    }
}

#[derive(Debug, Clone)]
pub enum WakeWordError {
    MissingAccessKey,
    BackendUnavailable,
    InvalidSensitivity(f32),
    ModelMissing(String),
    KeywordMissing(String),
    Native(String),
}

impl std::fmt::Display for WakeWordError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingAccessKey => write!(f, "Picovoice access key is not configured"),
            Self::BackendUnavailable => write!(f, "Porcupine wake-word backend is unavailable"),
            Self::InvalidSensitivity(value) => {
                write!(
                    f,
                    "Wake-word sensitivity must be between 0.0 and 1.0, got {value}"
                )
            }
            Self::ModelMissing(path) => write!(f, "Porcupine model not found at {path}"),
            Self::KeywordMissing(path) => write!(f, "Porcupine keyword file not found at {path}"),
            Self::Native(message) => write!(f, "{message}"),
        }
    }
}

impl std::error::Error for WakeWordError {}

pub struct WakeWordEngine {
    config: WakeWordConfig,
    backend: WakeWordBackend,
}

enum WakeWordBackend {
    Disabled,
    #[cfg(feature = "porcupine")]
    Porcupine(porcupine::PorcupineBackend),
}

impl WakeWordEngine {
    pub fn new(config: WakeWordConfig) -> Result<Self, WakeWordError> {
        validate_config(&config)?;

        #[cfg(feature = "porcupine")]
        {
            let backend = porcupine::PorcupineBackend::new(&config)?;
            Ok(Self {
                config,
                backend: WakeWordBackend::Porcupine(backend),
            })
        }

        #[cfg(not(feature = "porcupine"))]
        {
            let _ = &config;
            Err(WakeWordError::BackendUnavailable)
        }
    }

    pub fn disabled(config: WakeWordConfig) -> Self {
        Self {
            config,
            backend: WakeWordBackend::Disabled,
        }
    }

    pub fn is_configured(&self) -> bool {
        match &self.backend {
            WakeWordBackend::Disabled => false,
            #[cfg(feature = "porcupine")]
            WakeWordBackend::Porcupine(_) => true,
        }
    }

    pub fn keyword(&self) -> &str {
        &self.config.keyword
    }

    /// Process 16 kHz, 16-bit mono PCM. Returns true if wake word was detected.
    pub fn process_frame(&mut self, pcm: &[i16]) -> Result<bool, WakeWordError> {
        match &mut self.backend {
            WakeWordBackend::Disabled => Ok(false),
            #[cfg(feature = "porcupine")]
            WakeWordBackend::Porcupine(backend) => backend.process(pcm),
        }
    }
}

pub fn default_model_path() -> String {
    concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/vendor/porcupine/lib/common/porcupine_params.pv"
    )
    .into()
}

pub fn default_keyword_path(keyword: &str) -> String {
    let clean_keyword = keyword.trim().to_lowercase();
    let platform = if cfg!(target_os = "macos") {
        "mac"
    } else if cfg!(target_os = "linux") {
        "linux"
    } else if cfg!(target_os = "windows") {
        "windows"
    } else {
        ""
    };

    if platform.is_empty() {
        return clean_keyword;
    }

    format!(
        "{}/vendor/porcupine/resources/keyword_files/{}/{}_{}.ppn",
        env!("CARGO_MANIFEST_DIR"),
        platform,
        clean_keyword,
        platform
    )
}

fn validate_config(config: &WakeWordConfig) -> Result<(), WakeWordError> {
    if !(0.0..=1.0).contains(&config.sensitivity) {
        return Err(WakeWordError::InvalidSensitivity(config.sensitivity));
    }

    if config.access_key.as_deref().unwrap_or("").trim().is_empty() {
        return Err(WakeWordError::MissingAccessKey);
    }

    let model_path = config.model_path.clone().unwrap_or_else(default_model_path);
    if !Path::new(&model_path).exists() {
        return Err(WakeWordError::ModelMissing(model_path));
    }

    let keyword_path = config
        .keyword_path
        .clone()
        .unwrap_or_else(|| default_keyword_path(&config.keyword));
    if !Path::new(&keyword_path).exists() {
        return Err(WakeWordError::KeywordMissing(keyword_path));
    }

    Ok(())
}

#[cfg(feature = "porcupine")]
mod porcupine {
    use super::{default_keyword_path, default_model_path, WakeWordConfig, WakeWordError};
    use std::ffi::{CStr, CString};
    use std::os::raw::{c_char, c_float, c_int, c_void};
    use std::path::PathBuf;
    use std::ptr;

    const PV_STATUS_SUCCESS: c_int = 0;

    type PorcupineInit = unsafe extern "C" fn(
        *const c_char,
        *const c_char,
        *const c_char,
        c_int,
        *const *const c_char,
        *const c_float,
        *mut *mut c_void,
    ) -> c_int;
    type PorcupineDelete = unsafe extern "C" fn(*mut c_void);
    type PorcupineProcess = unsafe extern "C" fn(*mut c_void, *const i16, *mut c_int) -> c_int;
    type PorcupineFrameLength = unsafe extern "C" fn() -> c_int;
    type StatusToString = unsafe extern "C" fn(c_int) -> *const c_char;

    pub struct PorcupineBackend {
        _library: libloading::Library,
        handle: *mut c_void,
        frame_length: usize,
        pending: Vec<i16>,
        process: PorcupineProcess,
        delete: PorcupineDelete,
        status_to_string: StatusToString,
    }

    impl PorcupineBackend {
        pub fn new(config: &WakeWordConfig) -> Result<Self, WakeWordError> {
            let library = unsafe { libloading::Library::new(native_library_path()) }
                .map_err(|err| WakeWordError::Native(err.to_string()))?;
            let init = load_symbol::<PorcupineInit>(&library, b"pv_porcupine_init\0")?;
            let delete = load_symbol::<PorcupineDelete>(&library, b"pv_porcupine_delete\0")?;
            let process = load_symbol::<PorcupineProcess>(&library, b"pv_porcupine_process\0")?;
            let frame_length_fn =
                load_symbol::<PorcupineFrameLength>(&library, b"pv_porcupine_frame_length\0")?;
            let status_to_string =
                load_symbol::<StatusToString>(&library, b"pv_status_to_string\0")?;

            let access_key = CString::new(config.access_key.clone().unwrap_or_default())
                .map_err(|err| WakeWordError::Native(err.to_string()))?;
            let model_path =
                CString::new(config.model_path.clone().unwrap_or_else(default_model_path))
                    .map_err(|err| WakeWordError::Native(err.to_string()))?;
            let keyword_path = CString::new(
                config
                    .keyword_path
                    .clone()
                    .unwrap_or_else(|| default_keyword_path(&config.keyword)),
            )
            .map_err(|err| WakeWordError::Native(err.to_string()))?;
            let device = CString::new(config.device.clone())
                .map_err(|err| WakeWordError::Native(err.to_string()))?;
            let keyword_paths = [keyword_path.as_ptr()];
            let sensitivities = [config.sensitivity as c_float];
            let mut handle = ptr::null_mut();
            let status = unsafe {
                init(
                    access_key.as_ptr(),
                    model_path.as_ptr(),
                    device.as_ptr(),
                    1,
                    keyword_paths.as_ptr(),
                    sensitivities.as_ptr(),
                    &mut handle,
                )
            };
            if status != PV_STATUS_SUCCESS {
                return Err(WakeWordError::Native(status_message(
                    status,
                    status_to_string,
                )));
            }
            let frame_length = unsafe { frame_length_fn() };
            if frame_length <= 0 {
                unsafe { delete(handle) };
                return Err(WakeWordError::Native(
                    "Porcupine returned an invalid frame length".into(),
                ));
            }

            Ok(Self {
                _library: library,
                handle,
                frame_length: frame_length as usize,
                pending: Vec::new(),
                process,
                delete,
                status_to_string,
            })
        }

        pub fn process(&mut self, pcm: &[i16]) -> Result<bool, WakeWordError> {
            self.pending.extend_from_slice(pcm);
            let mut detected = false;
            while self.pending.len() >= self.frame_length {
                let mut keyword_index = -1;
                let status = unsafe {
                    (self.process)(self.handle, self.pending.as_ptr(), &mut keyword_index)
                };
                if status != PV_STATUS_SUCCESS {
                    return Err(WakeWordError::Native(status_message(
                        status,
                        self.status_to_string,
                    )));
                }
                if keyword_index >= 0 {
                    detected = true;
                }
                self.pending.drain(..self.frame_length);
            }
            Ok(detected)
        }
    }

    impl Drop for PorcupineBackend {
        fn drop(&mut self) {
            unsafe { (self.delete)(self.handle) };
        }
    }

    unsafe impl Send for PorcupineBackend {}

    fn native_library_path() -> PathBuf {
        let platform_dir = if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
            "mac/arm64"
        } else if cfg!(all(target_os = "macos", target_arch = "x86_64")) {
            "mac/x86_64"
        } else if cfg!(all(target_os = "linux", target_arch = "x86_64")) {
            "linux/x86_64"
        } else if cfg!(all(target_os = "windows", target_arch = "x86_64")) {
            "windows/amd64"
        } else if cfg!(all(target_os = "windows", target_arch = "aarch64")) {
            "windows/arm64"
        } else {
            ""
        };
        let file_name = if cfg!(target_os = "windows") {
            "libpv_porcupine.dll"
        } else if cfg!(target_os = "macos") {
            "libpv_porcupine.dylib"
        } else {
            "libpv_porcupine.so"
        };
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("vendor/porcupine/lib")
            .join(platform_dir)
            .join(file_name)
    }

    fn load_symbol<T: Copy>(
        library: &libloading::Library,
        symbol: &[u8],
    ) -> Result<T, WakeWordError> {
        unsafe { library.get::<T>(symbol) }
            .map(|symbol| *symbol)
            .map_err(|err| WakeWordError::Native(err.to_string()))
    }

    fn status_message(status: c_int, status_to_string: StatusToString) -> String {
        let message = unsafe { status_to_string(status) };
        if message.is_null() {
            return format!("Porcupine failed with status {status}");
        }
        unsafe { CStr::from_ptr(message) }
            .to_string_lossy()
            .into_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_missing_access_key() {
        let result = WakeWordEngine::new(WakeWordConfig {
            access_key: None,
            ..WakeWordConfig::default()
        });

        assert!(matches!(result, Err(WakeWordError::MissingAccessKey)));
    }

    #[test]
    fn rejects_invalid_sensitivity() {
        let result = WakeWordEngine::new(WakeWordConfig {
            sensitivity: 1.25,
            access_key: Some("test".into()),
            ..WakeWordConfig::default()
        });

        assert!(matches!(result, Err(WakeWordError::InvalidSensitivity(_))));
    }

    #[test]
    fn default_picovoice_keyword_path_exists() {
        assert!(Path::new(&default_keyword_path("picovoice")).exists());
    }

    #[test]
    fn disabled_engine_does_not_detect() {
        let mut engine = WakeWordEngine::disabled(WakeWordConfig::default());

        assert!(!engine.is_configured());
        assert!(!engine.process_frame(&[0, 1, -1]).unwrap());
    }
}
