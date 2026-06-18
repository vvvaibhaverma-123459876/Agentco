use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter};

static INFRA_RUNNING: AtomicBool = AtomicBool::new(false);

#[derive(serde::Serialize, Clone)]
pub struct InfraStatus {
    pub docker_running: bool,
    pub ollama_installed: bool,
    pub backend_running: bool,
    pub postgres_healthy: bool,
    pub kafka_healthy: bool,
    pub redis_healthy: bool,
}

/// Called from setup — drives the full launch sequence.
pub async fn run_startup(handle: &AppHandle) {
    emit(handle, "startup", "checking_docker");

    if !check_docker_internal() {
        emit(handle, "startup", "docker_missing");
        // Show window with wizard — user must install Docker
        show_window(handle);
        return;
    }
    emit(handle, "startup", "docker_ok");

    if !check_ollama_internal() {
        emit(handle, "startup", "ollama_missing");
        show_window(handle);
        return;
    }
    emit(handle, "startup", "ollama_ok");

    emit(handle, "startup", "starting_infrastructure");
    if let Err(e) = start_compose() {
        emit(handle, "startup_error", &e);
        show_window(handle);
        return;
    }
    emit(handle, "startup", "infrastructure_ready");

    // Run migrations
    emit(handle, "startup", "running_migrations");
    run_migrations();
    emit(handle, "startup", "migrations_done");

    // Start Node backend
    emit(handle, "startup", "starting_backend");
    crate::sidecar::spawn_backend(handle);
    emit(handle, "startup", "backend_started");

    INFRA_RUNNING.store(true, Ordering::SeqCst);
    emit(handle, "startup", "ready");

    // Show the main window
    show_window(handle);
    crate::tray::set_tray_status(handle, "green");
}

fn show_window(handle: &AppHandle) {
    if let Some(w) = handle.get_webview_window("main") {
        let _ = w.show();
        let _ = w.set_focus();
    }
}

fn emit(handle: &AppHandle, event: &str, payload: &str) {
    let _ = handle.emit(event, payload);
}

fn check_docker_internal() -> bool {
    Command::new("docker").args(["info"]).output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn check_ollama_internal() -> bool {
    Command::new("ollama").args(["list"]).output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn start_compose() -> Result<(), String> {
    let status = Command::new("docker")
        .args(["compose", "up", "-d"])
        .status()
        .map_err(|e| format!("Failed to run docker compose: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("docker compose up exited with status {status}"))
    }
}

fn stop_compose() {
    let _ = Command::new("docker")
        .args(["compose", "stop"])
        .status();
}

fn run_migrations() {
    // Node backend runs migrations on start via db/migrate.ts
    // Nothing extra needed here; kept as hook for future use
}

// ── Tauri commands ────────────────────────────────────────────────────────────

#[tauri::command]
pub fn check_docker() -> bool {
    check_docker_internal()
}

#[tauri::command]
pub fn check_ollama() -> bool {
    check_ollama_internal()
}

#[tauri::command]
pub async fn pull_model(model: String, window: tauri::Window) -> Result<(), String> {
    use std::io::{BufRead, BufReader};
    use std::process::Stdio;

    let mut child = Command::new("ollama")
        .args(["pull", &model])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("ollama pull failed: {e}"))?;

    if let Some(stdout) = child.stdout.take() {
        let reader = BufReader::new(stdout);
        for line in reader.lines().flatten() {
            let _ = window.emit("model_pull_progress", &line);
        }
    }

    let status = child.wait().map_err(|e| e.to_string())?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("ollama pull exited with status {status}"))
    }
}

#[tauri::command]
pub fn start_infrastructure() -> Result<(), String> {
    start_compose()
}

#[tauri::command]
pub fn stop_infrastructure() {
    stop_compose();
    INFRA_RUNNING.store(false, Ordering::SeqCst);
}

#[tauri::command]
pub async fn get_infra_status() -> InfraStatus {
    let docker_running = check_docker_internal();
    let ollama_installed = check_ollama_internal();

    // Probe services via TCP
    let postgres_healthy = port_open("127.0.0.1:5432");
    let kafka_healthy = port_open("127.0.0.1:9092");
    let redis_healthy = port_open("127.0.0.1:6379");

    // Check backend HTTP
    let backend_running = reqwest_check("http://localhost:3001/health").await;

    InfraStatus {
        docker_running,
        ollama_installed,
        backend_running,
        postgres_healthy,
        kafka_healthy,
        redis_healthy,
    }
}

fn port_open(addr: &str) -> bool {
    use std::net::TcpStream;
    use std::time::Duration;
    TcpStream::connect_timeout(&addr.parse().unwrap(), Duration::from_millis(300)).is_ok()
}

async fn reqwest_check(url: &str) -> bool {
    // Use std blocking check since we don't want to add reqwest dep just for this
    let addr = "127.0.0.1:3001";
    port_open(addr)
}
