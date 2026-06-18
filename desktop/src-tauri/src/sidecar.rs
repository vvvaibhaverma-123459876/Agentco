use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::AppHandle;

static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// Spawn the Node.js backend sidecar (bundled binary or npm start in dev).
pub fn spawn_backend(handle: &AppHandle) {
    let resource_dir = handle.path().resource_dir()
        .unwrap_or_else(|_| std::path::PathBuf::from("."));

    // In production: use the bundled node-backend binary
    // In dev: use `node dist/server.js` from backend/
    let backend_bin = resource_dir.join("binaries/node-backend");
    let mut cmd = if backend_bin.exists() {
        let mut c = Command::new(&backend_bin);
        c.env("PORT", "3001").env("NODE_ENV", "production");
        c
    } else {
        // Dev fallback: run from source
        let repo_root = resource_dir.ancestors()
            .find(|p| p.join("backend").exists())
            .unwrap_or(&resource_dir)
            .to_path_buf();
        let mut c = Command::new("node");
        c.arg(repo_root.join("backend/dist/server.js"))
         .env("PORT", "3001")
         .current_dir(&repo_root.join("backend"));
        c
    };

    cmd.stdout(Stdio::null()).stderr(Stdio::null());

    match cmd.spawn() {
        Ok(child) => {
            *BACKEND_PROCESS.lock().unwrap() = Some(child);
        }
        Err(e) => {
            eprintln!("[sidecar] Failed to spawn backend: {e}");
        }
    }
}

pub fn kill_backend() {
    if let Ok(mut guard) = BACKEND_PROCESS.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
        }
    }
}

// ── Tauri commands ────────────────────────────────────────────────────────────

#[tauri::command]
pub fn start_backend(handle: AppHandle) {
    spawn_backend(&handle);
}

#[tauri::command]
pub fn stop_backend() {
    kill_backend();
}
