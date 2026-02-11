fn main() {
    let manifest = tauri_build::AppManifest::new()
        .commands(&["generate_pdf_report", "read_tail_chunk"]);
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(manifest))
        .expect("error while building tauri application");
}
