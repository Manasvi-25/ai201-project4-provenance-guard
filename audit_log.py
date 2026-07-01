import json
import os
from datetime import datetime, timezone

LOG_FILE = "audit_log.json"

def _load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)

def _save_log(entries):
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def write_log_entry(entry: dict):
    entries = _load_log()
    entries.append(entry)
    _save_log(entries)

def get_log():
    return _load_log()

def update_log_entry(content_id: str, updates: dict) -> bool:
    """
    Finds the entry with matching content_id and applies updates to it.
    Returns True if found and updated, False otherwise.
    """
    entries = _load_log()
    for entry in entries:
        if entry["content_id"] == content_id:
            entry.update(updates)
            _save_log(entries)
            return True
    return False