use tauri_plugin_store::StoreExt;

#[tauri::command]
pub fn get_wizard_state(app: tauri::AppHandle) -> bool {
    let store = app.store("agentco-settings.json").unwrap();
    store.get("wizard_complete")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
}

#[tauri::command]
pub fn mark_wizard_complete(app: tauri::AppHandle) {
    let store = app.store("agentco-settings.json").unwrap();
    let _ = store.set("wizard_complete", serde_json::Value::Bool(true));
    let _ = store.save();
}
