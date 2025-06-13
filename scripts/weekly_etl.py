import io
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _save_excel_from_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract all XLS/XLSX files from *zf* into *dest* renamed as cot_{year}.xls."""
    for name in zf.namelist():
        if name.lower().endswith((".xls", ".xlsx")):
            match = re.search(r"(\d{4})", name)
            year = match.group(1) if match else Path(name).stem
            out = dest / f"cot_{year}.xls"
            with zf.open(name) as src, open(out, "wb") as dst:
                dst.write(src.read())


def download_year(year: int, dest: Path) -> None:
    """Download and extract a single year's COT Excel file."""
    url = f"https://www.cftc.gov/files/dea/history/fut_disagg_xls_{year}.zip"
    resp = requests.get(url)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            if name.lower().endswith((".xls", ".xlsx")):
                out = dest / f"cot_{year}.xls"
                with zf.open(name) as src, open(out, "wb") as dst:
                    dst.write(src.read())
                return
    raise RuntimeError(f"No .xls found in {url}")


def download_history(dest: Path) -> None:
    """Download 2006-2016 historical ZIP and extract all years."""
    url = "https://www.cftc.gov/files/dea/history/" "fut_disagg_xls_hist_2006_2016.zip"
    resp = requests.get(url)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        _save_excel_from_zip(zf, dest)


def upload_file(service, path: Path, folder_id: str) -> None:
    """Upload *path* to Google Drive *folder_id*."""
    file_metadata = {"name": path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(path))
    service.files().create(body=file_metadata, media_body=media).execute()


def main() -> int:
    creds_info = json.loads(os.environ["GDRIVE_SA_KEY"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive_service = build("drive", "v3", credentials=creds)

    raw_dir = Path(os.getenv("RAW_DATA_DIR", "src/data/raw"))
    raw_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RAW_DATA_FOLDER_ID", "")

    processed_dir = Path(os.getenv("PROCESSED_DIR", "src/data/processed"))
    processed_dir.mkdir(parents=True, exist_ok=True)
    processed_folder_id = os.getenv("PROCESSED_FOLDER_ID", "")

    out_csv = os.getenv(
        "OUT_CSV_PATH",
        str(processed_dir / "cot_disagg_futures_2006_2025.csv"),
    )

    end_year = 2025
    years = range(2017, end_year + 1)

    hist_years = range(2008, 2017)
    if any(not (raw_dir / f"cot_{y}.xls").exists() for y in hist_years):
        print("Downloading historical data 2006-2016…")
        download_history(raw_dir)

    for year in years:
        target = raw_dir / f"cot_{year}.xls"
        if not target.exists():
            print(f"Downloading {year}…")
            download_year(year, raw_dir)

    try:
        subprocess.check_call(
            [
                sys.executable,
                "src/data/make_dataset.py",
                "--raw-dir",
                str(raw_dir),
                "--out-csv",
                out_csv,
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.data.split_cot",
                "--in-csv",
                out_csv,
                "--gold",
                str(processed_dir / "cot_gold.csv"),
                "--crude",
                str(processed_dir / "cot_crude.csv"),
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.data.load_price",
                "--tickers",
                "GC=F,CL=F",
                "--max-retries",
                "5",
                "--retry-delay",
                "10",
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.data.merge_cot_price",
                "--cot",
                str(processed_dir / "cot_gold.csv"),
                "--price",
                str(Path("data/prices/gc_weekly.csv")),
                "--out",
                str(processed_dir / "merged_gc.csv"),
                "--market",
                "GOLD",
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.features.build_features",
                "--merged",
                str(processed_dir / "merged_gc.csv"),
                "--out",
                str(processed_dir / "features_gc.csv"),
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.data.build_classification_features",
                "--in",
                str(processed_dir / "features_gc.csv"),
                "--out",
                str(processed_dir / "class_features_gc_extreme.csv"),
                "--th",
                "0.95",
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.data.merge_cot_price",
                "--cot",
                str(processed_dir / "cot_crude.csv"),
                "--price",
                str(Path("data/prices/cl_weekly.csv")),
                "--out",
                str(processed_dir / "merged_cl.csv"),
                "--market",
                "CRUDE OIL",
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.features.build_features",
                "--merged",
                str(processed_dir / "merged_cl.csv"),
                "--out",
                str(processed_dir / "features_cl.csv"),
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "src.data.build_classification_features",
                "--in",
                str(processed_dir / "features_cl.csv"),
                "--out",
                str(processed_dir / "class_features_cl_extreme.csv"),
                "--th",
                "0.95",
            ]
        )

        if processed_folder_id:
            for csv in processed_dir.glob("*.csv"):
                upload_file(drive_service, csv, processed_folder_id)

    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
