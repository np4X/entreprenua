# Drive-backed backend (dumb version)

Same app as the root `client_app.py` / `machine_app.py` — same routes,
same templates, same points logic — except the SQLite database is kept
on Google Drive instead of only on local disk.

**How it works:** the local `waste.db` file here is just a cache.
Before every request, the app downloads the latest `waste.db` from a
Drive folder; after every request, it re-uploads the (possibly changed)
file back to Drive. See `gdrive_sync.py` for the code.

This is intentionally the "dumb" version of syncing: there's no
locking or conflict resolution, and every request pays a Drive
round-trip. It's fine for a single person clicking through a demo, not
for real concurrent traffic. Uploaded photos (`static/uploads/`) and
printed QR images (`static/qrcodes/`) are **not** synced to Drive —
only the database file is.

## What you need to set up (can't be done from here)

1. **Create a Google Cloud project** (or reuse one) at
   https://console.cloud.google.com/.
2. **Enable the Google Drive API** for that project (APIs & Services →
   Enable APIs → search "Google Drive API").
3. **Create a service account** (APIs & Services → Credentials → Create
   Credentials → Service account), then create a JSON key for it and
   download the file. Keep it out of this repo.
4. **Create (or pick) a folder in your own Google Drive** to hold
   `waste.db`, then **share that folder** with the service account's
   email address (looks like
   `something@your-project.iam.gserviceaccount.com`, found on the
   service account's page) with **Editor** access. This matters:
   service accounts have no storage quota of their own, so the file
   has to live in a folder owned by a real account.
5. **Copy the folder's id** out of its Google Drive URL:
   `https://drive.google.com/drive/folders/<FOLDER_ID>`.
6. Send me (or set locally) the path to the downloaded JSON key and
   that folder id — see environment variables below.

## Running it

```bash
pip install -r drive_backend/requirements.txt

export GDRIVE_CREDENTIALS_FILE=/path/to/service-account.json
export GDRIVE_FOLDER_ID=<folder id from step 5>

python drive_backend/machine_app.py   # in one terminal, port 5169 by default
python drive_backend/client_app.py    # in another terminal, port 5167 by default
```

If `GDRIVE_CREDENTIALS_FILE` / `GDRIVE_FOLDER_ID` aren't set, the sync
functions silently no-op and it behaves like a normal local-SQLite app
(handy for testing this folder's code without touching Drive at all).

Ports are 5167/5169 (rather than the root app's 5067/5069) so both
versions can run side by side without colliding.
