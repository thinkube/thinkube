/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

use std::process::Command;
use tauri::Manager;

#[tauri::command]
fn get_config_flags() -> (bool, bool) {
    let skip_config = std::env::var("SKIP_CONFIG").is_ok();
    let clean_state = std::env::var("CLEAN_STATE").is_ok();
    (skip_config, clean_state)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  // Start backend in development mode
  #[cfg(debug_assertions)]
  {
    println!("Starting FastAPI backend...");
    
    let backend_dir = std::env::current_dir()
      .unwrap()
      .parent()
      .unwrap()
      .parent()
      .unwrap()
      .join("backend");
    
    #[cfg(target_os = "linux")]
    {
      Command::new("bash")
        .arg("-c")
        .arg(format!("cd {} && source venv-test/bin/activate && python main.py", backend_dir.display()))
        .spawn()
        .expect("Failed to start backend");
    }
    
    #[cfg(target_os = "windows")]
    {
      Command::new("cmd")
        .arg("/C")
        .arg(format!("cd {} && venv-test\\Scripts\\activate && python main.py", backend_dir.display()))
        .spawn()
        .expect("Failed to start backend");
    }
    
    // Give backend time to start
    std::thread::sleep(std::time::Duration::from_secs(3));
  }

  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![get_config_flags])
    .setup(|app| {
      println!("Tauri setup starting...");
      
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      
      // Get the main window
      if let Some(window) = app.get_webview_window("main") {
        println!("Main window found, showing it...");
        window.show().unwrap();
        window.center().unwrap();
        window.set_focus().unwrap();
        
        // Open devtools in development mode
        #[cfg(debug_assertions)]
        {
          println!("Opening devtools...");
          window.open_devtools();
        }
      } else {
        println!("WARNING: Main window not found!");
      }
      
      println!("Tauri setup complete");
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
