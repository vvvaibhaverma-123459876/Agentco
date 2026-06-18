use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager,
};

pub fn setup_tray(handle: &AppHandle) -> tauri::Result<()> {
    let open_item = MenuItem::with_id(handle, "open", "Open AgentCo", true, None::<&str>)?;
    let separator1 = tauri::menu::PredefinedMenuItem::separator(handle)?;
    let start_item = MenuItem::with_id(handle, "start_run", "Start Autonomous Run", true, None::<&str>)?;
    let stop_item = MenuItem::with_id(handle, "stop_run", "Stop Run", false, None::<&str>)?;
    let separator2 = tauri::menu::PredefinedMenuItem::separator(handle)?;
    let settings_item = MenuItem::with_id(handle, "settings", "Settings", true, None::<&str>)?;
    let separator3 = tauri::menu::PredefinedMenuItem::separator(handle)?;
    let quit_item = MenuItem::with_id(handle, "quit", "Quit AgentCo", true, None::<&str>)?;

    let menu = Menu::with_items(
        handle,
        &[
            &open_item,
            &separator1,
            &start_item,
            &stop_item,
            &separator2,
            &settings_item,
            &separator3,
            &quit_item,
        ],
    )?;

    let _tray = TrayIconBuilder::with_id("main")
        .tooltip("AgentCo — starting...")
        .menu(&menu)
        .menu_on_left_click(false)
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.show();
                    let _ = w.set_focus();
                }
            }
            "start_run" => {
                let _ = app.emit("tray_start_run", ());
            }
            "stop_run" => {
                let _ = app.emit("tray_stop_run", ());
            }
            "settings" => {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.show();
                    let _ = w.eval("window.location.href='/settings'");
                }
            }
            "quit" => {
                // Graceful shutdown
                crate::lifecycle::stop_infrastructure();
                crate::sidecar::kill_backend();
                app.exit(0);
            }
            _ => {}
        })
        .build(handle)?;

    Ok(())
}

/// Update the tray icon to reflect system health: "green" | "yellow" | "red"
pub fn set_tray_status(handle: &AppHandle, status: &str) {
    let tooltip = match status {
        "green" => "AgentCo — running",
        "yellow" => "AgentCo — starting...",
        "red" => "AgentCo — error",
        _ => "AgentCo",
    };
    if let Some(tray) = handle.tray_by_id("main") {
        let _ = tray.set_tooltip(Some(tooltip));
    }
}
