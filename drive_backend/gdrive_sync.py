"""Thin, deliberately "dumb" sync layer between the local SQLite file and
a Google Drive folder.

There's no real-time database here — the whole waste.db file is
downloaded from Drive before each request and re-uploaded after each
request (see the before_request/after_request hooks in client_app.py and
machine_app.py). That means: no locking, no conflict resolution, and a
network round-trip on every request. Fine for a single-writer demo, not
for anything with real concurrent traffic.

Setup (see drive_backend/README.md for the full walkthrough):
  1. Create a Google Cloud service account with Drive API access and
     download its JSON key.
  2. Share a Drive folder with that service account's email address
     (Editor access) and copy the folder's id out of its URL.
  3. Set these environment variables before running client_app.py /
     machine_app.py:
       GDRIVE_CREDENTIALS_FILE  — path to the service account JSON key
       GDRIVE_FOLDER_ID         — id of the shared Drive folder

If those two variables aren't set, every function here is a no-op and
the app just falls back to a plain local SQLite file.
"""
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

SCOPES = ["https://www.googleapis.com/auth/drive"]
DB_FILENAME = os.environ.get("GDRIVE_DB_FILENAME", "waste.db")

_service_cache = None


def enabled():
    return bool(os.environ.get("GDRIVE_CREDENTIALS_FILE") and os.environ.get("GDRIVE_FOLDER_ID"))


def _service():
    global _service_cache
    if _service_cache is None:
        creds_path = os.environ["GDRIVE_CREDENTIALS_FILE"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        _service_cache = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _service_cache


def _find_file_id(service, folder_id):
    query = f"name = '{DB_FILENAME}' and '{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, spaces="drive", fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def download_db(local_path):
    """Pull the latest waste.db from Drive into local_path. No-op if
    Drive sync isn't configured, or if the file doesn't exist on Drive
    yet (first run — the local copy, if any, is left alone)."""
    if not enabled():
        return
    service = _service()
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    file_id = _find_file_id(service, folder_id)
    if not file_id:
        return
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    with open(local_path, "wb") as f:
        f.write(buf.getvalue())


def upload_db(local_path):
    """Push local_path up to Drive, creating the file there on first
    use. No-op if Drive sync isn't configured or the local file doesn't
    exist yet."""
    if not enabled() or not os.path.exists(local_path):
        return
    service = _service()
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    file_id = _find_file_id(service, folder_id)
    media = MediaFileUpload(local_path, mimetype="application/x-sqlite3", resumable=False)
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": DB_FILENAME, "parents": [folder_id]}
        service.files().create(body=metadata, media_body=media).execute()
