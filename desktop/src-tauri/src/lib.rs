mod lifecycle;
mod sidecar;
mod tray;
mod wizard;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|app| {
            let handle = app.handle().clone();

            // Build system tray
            tray::setup_tray(&handle)?;

            // Spawn the lifecycle manager (docker, backend, migrations)
            let handle2 = handle.clone();
            tauri::async_runtime::spawn(async move {
                lifecycle::run_startup(&handle2).await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            lifecycle::check_docker,
            lifecycle::check_ollama,
            lifecycle::pull_model,
            lifecycle::start_infrastructure,
            lifecycle::stop_infrastructure,
            lifecycle::get_infra_status,
            sidecar::start_backend,
            sidecar::stop_backend,
            wizard::get_wizard_state,
            wizard::mark_wizard_complete,
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Hide window instead of closing; quit via tray
                window.hide().unwrap();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running AgentCo");
}
