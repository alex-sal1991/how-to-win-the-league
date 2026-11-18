import json
from datetime import datetime
from pathlib import Path

def save_as_json(folder: str | Path, filename: str, file: dict | list) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    
    path = folder / f"{filename}_{datetime.now():%Y%m%d_%H%M%S}.json"
    
    if path.exists():
        print(f"{filename} already saved. File located in {folder}")
        return path
    
    path.write_text(json.dumps(file, indent=2), encoding="utf-8")
    print(f"{filename} has been saved to {folder}")
    return path

def read_json(filename: str | Path) -> dict:
    json_path = Path(filename)
    
    if not json_path.exists():
        raise FileNotFoundError(f"{json_path.name} not found in {json_path.parent}")
    
    return json.loads(json_path.read_text(encoding="utf-8"))
    
def latest_json(folder: str | Path, prefix: str) -> Path | None:
    """Newest '<prefix>_<timestamp>.json' in folder, or None if there isn't one."""
    files = sorted(Path(folder).glob(f"{prefix}_*.json"))
    return files[-1] if files else None   