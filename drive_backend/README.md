# Drive-backed backend (dumb version, no API)

Same app as the root `client_app.py` / `machine_app.py` — same routes,
same templates, same points logic — except `waste.db` is written into
a folder that **Google Drive for desktop** (the free sync client you
install on your PC/Mac, not the Drive API) keeps in sync on its own.
No Google Cloud project, no service account, no API calls, no billing.

**How it works:** `db.py` puts `waste.db` inside whatever folder the
`DRIVE_SYNC_DIR` environment variable points to. If that folder is one
Google Drive for desktop is already watching, Drive uploads the file
in the background every time the app writes to it — same as if you'd
dragged the file into Drive yourself. If `DRIVE_SYNC_DIR` isn't set, it
just falls back to a local `waste.db` next to this file, same as a
plain SQLite app.

This is still the "dumb" version: Drive's own sync is eventually
consistent (a save can take a few seconds to actually reach the
cloud), and if two machines write to the same synced file at nearly
the same time, Drive resolves that by creating a
`waste (1).db`-style **conflicted copy** rather than merging — it does
not lose data, but the two copies have to be reconciled by hand. Fine
for one person/one machine at a time, not for real concurrent writers.

## What you need to do

1. Install [Google Drive for desktop](https://www.google.com/drive/download/)
   and sign in, if you haven't already. This gives you a local folder
   (on Windows usually `G:\My Drive\...` or
   `C:\Users\<you>\Google Drive\My Drive\...`; on Mac usually
   `~/Google Drive/My Drive/...` — the exact path is whatever you chose
   during setup) that mirrors your Drive.
2. Pick or create a subfolder in there for this app's data, e.g.
   `.../My Drive/waste-app/`.
3. Tell me that folder's full local path (or just set it yourself, see
   below) — nothing else is needed, there's no key or id to hand over.

## Running it

```bash
pip install -r ../requirements.txt

export DRIVE_SYNC_DIR="/path/to/your/Google Drive/My Drive/waste-app"

python machine_app.py   # in one terminal, port 5169 by default
python client_app.py    # in another terminal, port 5167 by default
```

Leave `DRIVE_SYNC_DIR` unset to just run on a local `waste.db` here,
useful for testing this folder's code without Drive involved at all.

Ports are 5167/5169 (rather than the root app's 5067/5069) so both
versions can run side by side without colliding.
