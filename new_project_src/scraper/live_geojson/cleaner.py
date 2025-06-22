from pathlib import Path
import json

class LiveGeoJSONCleaner:
    def __init__(self, raw_json: Path, dest_dir: Path):
        self.raw     = raw_json
        self.dest_dir = dest_dir
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.cleaned = dest_dir / raw_json.with_suffix(".clean.json").name

    def clean(self) -> Path:
        data = json.loads(self.raw.read_text())
        features = data.get("features", [])

        out = {"type": "FeatureCollection", "features": features}
        with open(self.cleaned, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        print(f"✓ cleaned GeoJSON → {self.cleaned.name}")
        return self.cleaned
