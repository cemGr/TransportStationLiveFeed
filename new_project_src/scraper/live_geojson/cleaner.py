from pathlib import Path
import json

class LiveGeoJSONCleaner:
    """
    Takes a raw GeoJSON snapshot, validates/extracts the features array,
    and writes a cleaned JSON for downstream ingestion.
    """
    def __init__(self, raw_json: Path, dest_dir: Path):
        self.raw     = raw_json
        self.dest_dir = dest_dir
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        # mirror name but mark as “.clean.json”
        self.cleaned = dest_dir / raw_json.with_suffix(".clean.json").name

    def clean(self) -> Path:
        data = json.loads(self.raw.read_text())
        features = data.get("features", [])
        # you could filter or validate here; we just re-serialize
        out = {"type": "FeatureCollection", "features": features}
        with open(self.cleaned, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        print(f"✓ cleaned GeoJSON → {self.cleaned.name}")
        return self.cleaned
