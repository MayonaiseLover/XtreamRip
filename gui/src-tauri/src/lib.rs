use std::path::PathBuf;
use futures_util::StreamExt;
use tokio::fs::File;
use tokio::io::AsyncWriteExt;
use std::sync::Arc;
use tokio::sync::{Mutex, Semaphore};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, State};

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct DownloadItem {
    pub id: String,
    pub url: String,
    pub dest: String,
    pub name: String,
    pub status: String,
    pub progress: u8,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct AppSettings {
    pub workers: usize,
    pub download_dir: String,
}

pub struct AppState {
    pub queue: Arc<Mutex<Vec<DownloadItem>>>,
    pub settings: Arc<Mutex<AppSettings>>,
    pub semaphore: Arc<Semaphore>,
}

#[tauri::command]
async fn get_settings(state: State<'_, AppState>) -> Result<AppSettings, String> {
    let s = state.settings.lock().await;
    Ok(s.clone())
}

#[tauri::command]
async fn set_settings(state: State<'_, AppState>, settings: AppSettings) -> Result<(), String> {
    let mut s = state.settings.lock().await;
    // Note: To dynamically change semaphore permits, we would need to recreate it or use dynamically sized semaphores. 
    // For simplicity, we just save the setting. Changes to workers require app restart to fully apply perfectly, 
    // or we can handle it manually. But for now, we just save it.
    *s = settings.clone();
    
    // Save to disk (simple json)
    if let Some(dirs) = dirs::config_dir() {
        let p = dirs.join("xtreamrip").join("settings.json");
        if let Ok(js) = serde_json::to_string_pretty(&settings) {
            let _ = std::fs::create_dir_all(p.parent().unwrap());
            let _ = std::fs::write(p, js);
        }
    }
    Ok(())
}

#[tauri::command]
async fn get_queue(state: State<'_, AppState>) -> Result<Vec<DownloadItem>, String> {
    let q = state.queue.lock().await;
    Ok(q.clone())
}

#[tauri::command]
async fn add_to_queue(
    app: AppHandle,
    state: State<'_, AppState>,
    url: String,
    dest: String,
    name: String,
) -> Result<String, String> {
    let id = format!("{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis());
    let item = DownloadItem {
        id: id.clone(),
        url,
        dest: dest.clone(),
        name,
        status: "Pending".to_string(),
        progress: 0,
    };
    
    {
        let mut q = state.queue.lock().await;
        q.push(item.clone());
    }
    
    app.emit("download-update", ()).unwrap();
    
    let queue_arc = state.queue.clone();
    let sem_arc = state.semaphore.clone();
    let id_clone = id.clone();
    
    tokio::spawn(async move {
        let _permit = sem_arc.acquire().await.unwrap();
        
        // update status to Downloading
        {
            let mut q = queue_arc.lock().await;
            if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                i.status = "Downloading".to_string();
            }
        }
        app.emit("download-update", ()).unwrap();
        
        let path = PathBuf::from(&dest);
        let _ = tokio::fs::create_dir_all(path.parent().unwrap()).await;
        
        let mut resume = 0;
        if path.exists() {
            if let Ok(meta) = tokio::fs::metadata(&path).await {
                resume = meta.len();
            }
        }
        
        let client = reqwest::Client::new();
        let mut req = client.get(&item.url);
        if resume > 0 {
            req = req.header("Range", format!("bytes={}-", resume));
        }
        
        match req.send().await {
            Ok(mut res) => {
                if res.status() == reqwest::StatusCode::RANGE_NOT_SATISFIABLE {
                    // Already downloaded
                    let mut q = queue_arc.lock().await;
                    if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                        i.status = "Done".to_string();
                        i.progress = 100;
                    }
                    let _ = app.emit("download-update", ());
                    return;
                }
                
                let total_size = res.content_length().unwrap_or(0) + resume;
                let mut current_size = resume;
                
                let mut file = match File::options().create(true).append(resume > 0).write(resume == 0).open(&path).await {
                    Ok(f) => f,
                    Err(e) => {
                        let mut q = queue_arc.lock().await;
                        if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                            i.status = format!("Error: {}", e);
                        }
                        let _ = app.emit("download-update", ());
                        return;
                    }
                };

                let mut last_emit = std::time::Instant::now();
                while let Some(chunk) = res.chunk().await.unwrap_or(None) {
                    if let Err(e) = file.write_all(&chunk).await {
                        let mut q = queue_arc.lock().await;
                        if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                            i.status = format!("Error: {}", e);
                        }
                        let _ = app.emit("download-update", ());
                        return;
                    }
                    current_size += chunk.len() as u64;
                    let pct = if total_size > 0 { ((current_size as f64 / total_size as f64) * 100.0) as u8 } else { 0 };
                    
                    if last_emit.elapsed().as_millis() > 500 {
                        last_emit = std::time::Instant::now();
                        let mut q = queue_arc.lock().await;
                        if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                            i.progress = pct;
                        }
                        let _ = app.emit("download-update", ());
                    }
                }
                
                {
                    let mut q = queue_arc.lock().await;
                    if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                        i.status = "Done".to_string();
                        i.progress = 100;
                    }
                }
                let _ = app.emit("download-update", ());
            },
            Err(e) => {
                let mut q = queue_arc.lock().await;
                if let Some(i) = q.iter_mut().find(|x| x.id == id_clone) {
                    i.status = format!("Error: {}", e);
                }
                let _ = app.emit("download-update", ());
            }
        }
    });
    
    Ok(id)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut default_settings = AppSettings {
        workers: 1,
        download_dir: "".to_string(), // Frontend handles default
    };

    if let Some(dirs) = dirs::config_dir() {
        if let Ok(d) = std::fs::read_to_string(dirs.join("xtreamrip").join("settings.json")) {
            if let Ok(s) = serde_json::from_str::<AppSettings>(&d) {
                default_settings = s;
            }
        }
    }

    // Default to downloading inside the users Downloads/XtreamRip directory if empty
    if default_settings.download_dir.is_empty() {
        if let Some(dirs) = dirs::download_dir() {
            default_settings.download_dir = dirs.join("XtreamRip").to_string_lossy().to_string();
        }
    }

    let sem_workers = if default_settings.workers > 0 { default_settings.workers } else { 1 };
    
    let app_state = AppState {
        queue: Arc::new(Mutex::new(Vec::new())),
        settings: Arc::new(Mutex::new(default_settings)),
        semaphore: Arc::new(Semaphore::new(sem_workers)),
    };

    tauri::Builder::default()
        .manage(app_state)
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            add_to_queue,
            get_queue,
            get_settings,
            set_settings
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
