import json
from pathlib import Path
from backend.app.core.config import settings
def load_json(name: str):
    return json.loads((Path(settings.data_dir) / "processed" / name).read_text(encoding="utf-8"))
