#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use chrono::Utc;
use printpdf::*;
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::BufWriter;
use std::io::{Read, Seek, SeekFrom};

#[derive(Debug, Serialize, Deserialize)]
struct ReportRow {
    timestamp: String,
    action: String,
    category: String,
    user: String,
    status: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ReportPayload {
    total: u32,
    success: u32,
    failure: u32,
    top_categories: Vec<(String, u32)>,
    top_users: Vec<(String, u32)>,
    top_actions: Vec<(String, u32)>,
    rows: Vec<ReportRow>,
}

#[tauri::command]
fn generate_pdf_report(path: String, payload: ReportPayload) -> Result<(), String> {
    let (doc, page1, layer1) =
        PdfDocument::new("Audit Report", Mm(210.0), Mm(297.0), "Layer 1");
    let current_layer = doc.get_page(page1).get_layer(layer1);

    let font = doc
        .add_builtin_font(BuiltinFont::Helvetica)
        .map_err(|e| e.to_string())?;

    let mut y = 285.0;
    let line = 6.0;

    current_layer.use_text("Audit Report", 18.0, Mm(20.0), Mm(y), &font);
    y -= 10.0;
    current_layer.use_text(
        format!("Generated {}", Utc::now().to_rfc3339()),
        10.0,
        Mm(20.0),
        Mm(y),
        &font,
    );
    y -= 12.0;

    current_layer.use_text(
        format!("Total: {}  Success: {}  Failure: {}", payload.total, payload.success, payload.failure),
        11.0,
        Mm(20.0),
        Mm(y),
        &font,
    );
    y -= 10.0;

    fn section_title(layer: &PdfLayerReference, font: &IndirectFontRef, title: &str, y: &mut f64) {
        layer.use_text(title, 12.0, Mm(20.0), Mm(*y), font);
        *y -= 8.0;
    }

    section_title(&current_layer, &font, "Top Categories", &mut y);
    for (k, v) in payload.top_categories.iter().take(5) {
        current_layer.use_text(format!("{}: {}", k, v), 10.0, Mm(24.0), Mm(y), &font);
        y -= line;
    }
    y -= 4.0;

    section_title(&current_layer, &font, "Top Users", &mut y);
    for (k, v) in payload.top_users.iter().take(5) {
        current_layer.use_text(format!("{}: {}", k, v), 10.0, Mm(24.0), Mm(y), &font);
        y -= line;
    }
    y -= 4.0;

    section_title(&current_layer, &font, "Top Actions", &mut y);
    for (k, v) in payload.top_actions.iter().take(5) {
        current_layer.use_text(format!("{}: {}", k, v), 10.0, Mm(24.0), Mm(y), &font);
        y -= line;
    }
    y -= 6.0;

    section_title(&current_layer, &font, "Events (first 100)", &mut y);
    for row in payload.rows.iter().take(100) {
        let line_text = format!(
            "{} | {} | {} | {} | {}",
            row.timestamp, row.action, row.category, row.user, row.status
        );
        current_layer.use_text(line_text, 8.0, Mm(20.0), Mm(y), &font);
        y -= 4.5;
        if y < 20.0 {
            break;
        }
    }

    let mut buffer = BufWriter::new(File::create(path).map_err(|e| e.to_string())?);
    doc.save(&mut buffer).map_err(|e| e.to_string())
}

#[tauri::command]
fn read_tail_chunk(path: String, offset: u64) -> Result<(String, u64), String> {
    let mut file = File::open(path).map_err(|e| e.to_string())?;
    let metadata = file.metadata().map_err(|e| e.to_string())?;
    let file_len = metadata.len();

    if offset >= file_len {
        return Ok(("".to_string(), file_len));
    }

    file.seek(SeekFrom::Start(offset))
        .map_err(|e| e.to_string())?;
    let mut buf = String::new();
    file.read_to_string(&mut buf).map_err(|e| e.to_string())?;
    Ok((buf, file_len))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![generate_pdf_report, read_tail_chunk])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
