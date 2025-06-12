import os
import sys
import io
import json
import zipfile
import requests
import subprocess
from datetime import datetime
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build


def download_year(year: int, dest: Path) -> None:
    """Download and extract a single year's COT Excel file."""
    url = f"https://www.cftc.gov/files/dea/history/futonly_xls_{year}.zip"
    resp = requests.get(url)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".xls"):
                out = dest / f"cot_{year}.xls"
                with zf.open(name) as src, open(out, "wb") as dst:
                    dst.write(src.read())
                return
    raise RuntimeError(f"No .xls found in {url}")


def main() -> int:
    creds_info = json.loads(os.environ["GDRIVE_SA_KEY"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive = build("drive", "v3", credentials=creds)  # noqa: F841 unused but kept

    raw_dir = Path(os.getenv("RAW_DATA_DIR", "src/data/raw"))
    raw_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RAW_DATA_FOLDER_ID", "")  # ensure var exists

    for year in range(2008, datetime.now().year + 1):
        target = raw_dir / f"cot_{year}.xls"
        if not target.exists():
            download_year(year, raw_dir)

    try:
        subprocess.check_call([
            sys.executable, "src/data/make_dataset.py",
            "--raw-dir", str(raw_dir),
            "--out-csv", "src/data/processed/cot_disagg_futures_2016_2025.csv",
        ])
        subprocess.check_call([
            sys.executable, "-m", "src.data.split_cot",
            "--in-csv", "src/data/processed/cot_disagg_futures_2016_2025.csv",
            "--gold", "src/data/processed/cot_gold.csv",
            "--crude", "src/data/processed/cot_crude.csv",
        ])
        subprocess.check_call([
            sys.executable, "-m", "src.data.load_price",
            "--tickers", "GC=F,CL=F",
            "--max-retries", "5",
            "--retry-delay", "10",
        ])
        subprocess.check_call([
            sys.executable, "-m", "src.data.build_classification_features",
            "--in", "src/data/processed/class_features_gc.csv",
            "--out", "src/data/processed/class_features_gc_extreme.csv",
            "--th", "0.95",
        ])
        subprocess.check_call([
            sys.executable, "-m", "src.data.build_classification_features",
            "--in", "src/data/processed/class_features_cl.csv",
            "--out", "src/data/processed/class_features_cl_extreme.csv",
            "--th", "0.95",
        ])
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
