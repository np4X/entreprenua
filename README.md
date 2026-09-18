# แยกขยะได้แต้ม — Waste Sorting Rewards App

A prototype web app for solving Bangkok's mixed-waste problem: residents scan a
QR code on their trash bag, report what type of waste is inside (with as much
detail as they like), and earn points redeemable for rewards (Grab/Shopee
discounts, common-fee discounts, etc.). Waste is double-checked by AI and by
the waste collection staff, and residents who misreport or fake their sorting
are penalized.

Built with Python (Flask) and plain HTML/CSS/JS — no frontend framework, no
build step.

## How it's split

The system is two separate Flask apps sharing one SQLite database, matching
the two physical devices involved:

| App | Runs on | Port | Screens |
|---|---|---|---|
| `client_app.py` | The resident's **phone** | 5067 | Home, scan the bag's QR (camera), choose category, take the mandatory photo, waiting screens, verification result + points, rewards wallet, profile |
| `machine_app.py` | The **PC next to the smart bin** | 5069 | Idle screen, displays the printed QR (passive — the resident confirms attaching it from their phone), opens the bin lid, staff review console (`/staff`) |

Both processes read/write the same `waste.db` SQLite file directly — no
network calls between them are needed since they normally run on the same PC.

## Setup

```bash
git clone https://github.com/np4X/entreprenua.git
cd entreprenua
pip install -r requirements.txt
python machine_app.py   # in one terminal
python client_app.py    # in another terminal
```

Both apps read `APP_HOST` / `APP_PORT` environment variables if you want to
override the defaults (`0.0.0.0:5069` and `0.0.0.0:5067`).

## Live click-through demo (GitHub Pages)

A static, click-through demo of just the resident-facing screens is in
`client/` and runs entirely in the browser via
[PyScript](https://pyscript.net/) (Python compiled to WebAssembly) — no
server, no real database, no real machine involved. It's meant purely to
show the flow to someone without them installing Python.

**Live at:** https://np4x.github.io/entreprenua/client/

(Pages is configured to deploy from the repo root rather than `/client`,
which is why `/client/` is part of the URL — that also means the root URL,
https://np4x.github.io/entreprenua/, just shows this README instead.)

The demo re-implements the same category/points rules as `db.py`, but all
state lives only in your browser tab (refresh = reset) — it does not talk
to `client_app.py` / `machine_app.py` at all.

## User flow

1. **Home** (phone) — resident taps "ทิ้งขยะตอนนี้" (throw trash now).
2. **Print QR** (machine, passive display) — the machine shows a one-time QR
   code. The resident peels off the sticker and attaches it to their bag,
   then confirms on their **phone** — the machine returns to idle by itself.
3. **Scan + categorize** (phone) — resident takes a photo of the QR sticker
   (decoded client-side with the vendored `jsQR` library — works fully
   offline), then picks a category: เศษอาหาร (food waste) / รีไซเคิล
   (recycle) / ทั่วไป (general).
4. **Photo + note** (phone) — mandatory photo of the bag's contents, plus an
   optional detail note (more detail = more points).
5. **Bin opens** (machine) — resident inserts the bag; the machine runs a
   mock AI check and queues the bag for staff review.
6. **Verification + points** (phone) — live-polls until staff confirm or
   penalize the report.
7. **Rewards** (phone) — redeem accumulated points.

## Points logic (`db.py`)

- Base points by category: food = 10, recycle = 15, general = 5.
- +5 bonus if the resident's detail note is ≥8 characters.
- −20 penalty (and a flag on their profile) if staff catch a mismatched or
  faked report.

## Notes for further development

- `app.secret_key` in both apps is a placeholder (`"dev-secret-change-me"`) —
  set a real secret before any real deployment.
- The AI check in `machine_app.py` (`run_mock_ai_check`) is a random
  stand-in for a real image-classification model.
- `smoke_test.py` drives both apps together end-to-end against a scratch
  database — run it after making changes: `python smoke_test.py`.
