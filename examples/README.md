Prototype Examples

This folder contains a working prototype app that demonstrates:
- Direct API logging
- Decorator-based logging
- Context manager logging with exception capture
- PII sanitization (emails, passwords, SSNs, credit cards)
- Custom in-memory backend to show extensibility
- YAML config for file backend and format selection

Run
  python examples/prototype_app.py
  python examples/prototype_app.py --config examples/prototype_config.yaml

Notes
- Default logs go to ./logs/audit
- Config format can be json, jsonl, csv, or text
