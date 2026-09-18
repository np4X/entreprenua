# แยกขยะได้แต้ม — Waste Sorting Rewards App

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
