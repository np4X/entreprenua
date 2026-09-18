import os

import db
import client_app
import machine_app

TEST_DB = os.path.join(os.path.dirname(__file__), "waste.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

db.init_db()
client_app.app.testing = True
machine_app.app.testing = True
client = client_app.app.test_client()
machine = machine_app.app.test_client()

TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# --- client: home + start bag ---
r = client.get("/")
assert r.status_code == 200
print("client home OK")

r = client.post("/start_bag", follow_redirects=True)
assert r.status_code == 200
with client.session_transaction() as sess:
    bag_id = sess["bag_id"]
bag = db.get_bag_with_status("created")
assert bag is not None and bag["id"] == bag_id
print("bag created:", bag["code"], bag["status"])

# --- client: should be waiting, since machine hasn't tagged it yet ---
r = client.get("/waiting_print")
assert r.status_code == 200
print("client shows waiting_print while status=created")

# --- machine: idle should redirect to print_qr (passive display, no button) ---
r = machine.get("/", follow_redirects=False)
assert r.status_code == 302 and "/print_qr" in r.headers["Location"]
r = machine.get("/print_qr")
assert r.status_code == 200
assert bag["code"].encode() in r.data
print("machine shows print_qr for the pending bag (display only)")

r = machine.get(f"/print_qr/status/{bag_id}")
assert r.get_json()["status"] == "created"
print("machine print_qr/status still 'created' before phone confirms")

# --- client (phone) confirms it attached the sticker -- this is what advances the bag ---
r = client.post("/waiting_print/confirm", follow_redirects=True)
assert r.status_code == 200
conn = db.get_db()
bag = dict(conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone())
conn.close()
assert bag["status"] == "tagged"
print("client confirmed attach -> bag status:", bag["status"])

r = machine.get(f"/print_qr/status/{bag_id}")
assert r.get_json()["status"] == "tagged"
print("machine print_qr/status now sees 'tagged' (would return to idle)")

# --- machine idle now has nothing to do ---
r = machine.get("/")
assert r.status_code == 200  # renders idle.html, no redirect
print("machine idle (nothing pending)")


# --- client continues: scan (camera-only, no QR shown), category, photo ---
r = client.post("/scan/verify_code", json={"code": bag["code"]})
assert r.get_json()["ok"] is True
print("client scan verify OK (no QR display/generation on client)")

r = client.post("/scan/category", data={"category": "food"}, follow_redirects=True)
assert r.status_code == 200
conn = db.get_db()
bag = dict(conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone())
conn.close()
assert bag["category"] == "food"
print("category set:", bag["category"])

r = client.post(
    "/photo/upload",
    json={"image_data": TINY_PNG, "note": "แยกเศษอาหารออกจากถุงพลาสติกแล้ว"},
)
data = r.get_json()
assert data["ok"] is True, data
print("photo uploaded ->", data["redirect"])

# --- client now waits for machine to open bin ---
r = client.get("/waiting_bin")
assert r.status_code == 200
print("client shows waiting_bin while status=photographed")

# --- machine: idle should redirect to bin_open ---
r = machine.get("/", follow_redirects=False)
assert r.status_code == 302 and "/bin_open" in r.headers["Location"]
r = machine.get("/bin_open")
assert r.status_code == 200
print("machine shows bin_open for the pending bag")

r = machine.post(f"/bin_open/done/{bag_id}", follow_redirects=True)
assert r.status_code == 200
conn = db.get_db()
bag = dict(conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone())
conn.close()
assert bag["status"] == "pending_staff"
print("machine opened bin + ran AI check -> status:", bag["status"], "ai_result:", bag["ai_result"])

# --- client: waiting_bin/status should now report not 'photographed' ---
r = client.get("/waiting_bin/status")
assert r.get_json()["status"] == "pending_staff"
print("client waiting_bin/status sees pending_staff")

# --- machine staff dashboard shows it, confirms it ---
r = machine.get("/staff")
assert r.status_code == 200
assert bag["code"].encode() in r.data
print("machine staff dashboard shows pending bag")

r = machine.post(f"/staff/{bag_id}/confirm", follow_redirects=True)
assert r.status_code == 200
conn = db.get_db()
bag = dict(conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone())
user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (bag["user_id"],)).fetchone())
conn.close()
print("after staff confirm: status =", bag["status"], "points_awarded =", bag["points_awarded"])
assert bag["points_awarded"] == 10 + 5  # food(10) + detail bonus(5)
print("user points after confirm:", user["points"])

# --- client sees final verified state + can redeem ---
r = client.get("/verify/status")
vs = r.get_json()
assert vs["status"] == "verified"
print("client verify status:", vs)

conn = db.get_db()
reward = conn.execute("SELECT * FROM rewards ORDER BY cost ASC LIMIT 1").fetchone()
conn.close()
r = client.post(f"/rewards/redeem/{reward['id']}", follow_redirects=True)
assert r.status_code == 200
conn = db.get_db()
user2 = dict(conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone())
conn.close()
print(f"redeemed '{reward['name']}' for {reward['cost']} -> points now {user2['points']}")
assert user2["points"] == user["points"] - reward["cost"]

print("\nALL SMOKE TESTS PASSED (client_app + machine_app, shared DB)")
