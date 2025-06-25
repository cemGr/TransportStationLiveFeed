from pathlib import Path
import pandas as pd

class StationCleaner:

    def __init__(self, raw_csv: Path, proc_dir: Path):
        self.raw_csv  = raw_csv
        self.proc_dir = proc_dir
        self.proc_dir.mkdir(parents=True, exist_ok=True)
        self.out_csv  = proc_dir / "cleaned_station_data.csv"

    def clean(self) -> Path | None:
        if self.out_csv.exists():
            return None

        df = (
            pd.read_csv(self.raw_csv, encoding="latin-1")
              .rename(columns=str.strip)
              .drop_duplicates(subset=["Kiosk ID"])
        )
        df["Region"].fillna("Unknown", inplace=True)
        df["Kiosk Name"].fillna("Unnamed Station", inplace=True)
        df["Status"].fillna("Unknown", inplace=True)
        df = df.drop(columns=["Go Live Date", "status2"], errors="ignore")

        df.to_csv(self.out_csv, index=False)
        print(f"✓ cleaned station CSV → {self.out_csv}")
        return self.out_csv
