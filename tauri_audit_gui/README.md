Audit GUI Prototype (Tauri-Ready)

This is a lightweight GUI prototype designed for non-technical users to explore audit logs,
learn what each field means, and follow a guided tutorial.

Key features
- Open audit log files (JSON, JSONL, CSV)
- Friendly explanations for every field
- Filter/search by action, category, user, status
- Tutorial mode for guided onboarding
- Export filtered results to JSON/CSV
- Summary panel with top categories/users/actions
- Setup wizard that generates YAML config
- Sorting, pagination, date range filters, and printable report
- Exportable HTML report (print or save as PDF from browser)
- Saved views, insights, validation checks, and help shortcuts
- Native PDF export in Tauri desktop mode
- Live tail for JSONL logs (Tauri desktop mode)
- Bookmarks and notes on events (saved locally)
- Multi-file merge with source tagging
- Regex search and query DSL (e.g. `action:login user:alice status:FAILURE`)
- Integrity chain summary (SHA-256 hash chain)
- Stacked timeline by source + integrity detail list
- Regex presets (Failures, Logins, Errors)

Run as static (quick preview)
1. Open `tauri_audit_gui/index.html` in a browser.

Run as Tauri (desktop)
1. Install Rust + Tauri CLI (v2)
2. Start a static server:
   - `python -m http.server 1420 -d tauri_audit_gui`
3. From `tauri_audit_gui/src-tauri`:
   - `cargo tauri dev`

Notes
- The UI is deliberately framework-free to keep setup simple.
- The file parser supports basic CSV. For complex CSVs, prefer JSONL.
- Try the sample log: `tauri_audit_gui/sample_logs.jsonl`.
- PDF export uses the native Tauri backend and is available only in desktop mode.
- Live tail uses the `fs` plugin and requires file read permissions.
