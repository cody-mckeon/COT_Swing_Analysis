# This script is intended to run in GitHub Actions or a Docker container.
# Ensure `GDRIVE_SA_KEY`, `RAW_DATA_FOLDER_ID` and `RAW_DATA_DIR` are set.
# TODO: add a Dockerfile to containerize this script.

import os
import sys
import json
import io
import logging
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

IS_COLAB = os.getenv("COLAB_ENV") == "1"
if IS_COLAB:
    RAW_DIR = Path("/content/drive/MyDrive/COT_Swing_Analysis/src/data/raw")
else:
    RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "src/data/raw"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_drive_service():
    key_json = os.getenv("GDRIVE_SA_KEY")
    if not key_json:
        logging.error({"error": "GDRIVE_SA_KEY not set"})
        sys.exit(1)

    info = json.loads(key_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)


def download_folder(service, folder_id: str, dest_dir: Path) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    query = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'"
    try:
        files = service.files().list(q=query, fields="files(id, name)").execute().get("files", [])
    except HttpError as e:
        logging.error({"error": str(e)})
        return 1

    for f in files:
        dest_file = dest_dir / f["name"]
        request = service.files().get_media(fileId=f["id"])
        fh: Optional[io.FileIO] = None
        try:
            fh = io.FileIO(dest_file, "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            logging.info({"downloaded": dest_file.as_posix()})
        except HttpError as e:
            logging.error({"file": f["name"], "error": str(e)})
            return 1
        finally:
            if fh:
                fh.close()
    return 0


def main() -> None:
    folder_id = os.getenv("RAW_DATA_FOLDER_ID")
    if not folder_id:
        logging.error({"error": "RAW_DATA_FOLDER_ID not set"})
        sys.exit(1)

    service = build_drive_service()
    exit_code = download_folder(service, folder_id, RAW_DIR)
    sys.exit(exit_code)


if __name__ == "__main__":
    if IS_COLAB:
        from google.colab import drive
        drive.mount("/content/drive")
    main()
