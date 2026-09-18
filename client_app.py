"""Client app — runs on the RESIDENT'S PHONE.

Handles: home, scanning the bag's QR (camera only — the QR itself is
printed by the machine app, never generated here), choosing a
category, taking the mandatory photo, waiting for the machine to do
its physical steps, viewing verification results, and the rewards
wallet. Shares the same SQLite database as machine_app.py.
"""
import base64
import os

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash

import db
from db import CATEGORY_LABELS, BASE_POINTS, DETAIL_BONUS, DETAIL_MIN_LEN

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

UPLOAD_DIR = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def current_user():
    conn = db.get_db()
    row = None
    if "user_id" in session:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if row is None:
        conn.close()
        user = db.get_or_create_demo_user()
        session["user_id"] = user["id"]
        session.pop("bag_id", None)
        return user
    conn.close()
    return dict(row)


def get_bag(bag_id):
    if not bag_id:
        return None
    conn = db.get_db()
    row = conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- Home ----------
@app.route("/")
def home():
    user = current_user()
    conn = db.get_db()
    last_bag = conn.execute(
        "SELECT * FROM bags WHERE user_id = ? AND status = 'verified' "
        "ORDER BY id DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    conn.close()
    return render_template(
        "home.html",
        user=user,
        last_bag=dict(last_bag) if last_bag else None,
        category_labels=CATEGORY_LABELS,
    )


@app.route("/start_bag", methods=["POST"])
def start_bag():
    user = current_user()
    conn = db.get_db()
    cur = conn.execute(
        "INSERT INTO bags (code, user_id, status) VALUES (?, ?, 'created')",
        (db.new_bag_code(), user["id"]),
    )
    conn.commit()
    bag_id = cur.lastrowid
    conn.close()
    session["bag_id"] = bag_id
    return redirect(url_for("waiting_print"))


# ---------- Attach QR sticker ----------
# The machine only DISPLAYS the QR (it has no button of its own). The
# resident confirms "I've attached it" here, on their phone, which is
# what actually advances the bag to 'tagged' and lets the machine's
# screen return to idle on its next poll.
@app.route("/waiting_print")
def waiting_print():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return redirect(url_for("home"))
    if bag["status"] != "created":
        return redirect(url_for("scan"))
    return render_template("waiting_print.html", bag=bag)


@app.route("/waiting_print/confirm", methods=["POST"])
def waiting_print_confirm():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return redirect(url_for("home"))
    conn = db.get_db()
    conn.execute("UPDATE bags SET status = 'tagged' WHERE id = ?", (bag["id"],))
    conn.commit()
    conn.close()
    return redirect(url_for("scan"))


# ---------- Scan bag QR (camera only) + choose category ----------
@app.route("/scan")
def scan():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return redirect(url_for("home"))
    return render_template("scan.html", bag=bag, category_labels=CATEGORY_LABELS)


@app.route("/scan/verify_code", methods=["POST"])
def scan_verify_code():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return jsonify({"ok": False, "message": "ไม่พบถุงที่กำลังทิ้ง"}), 400
    scanned = (request.json or {}).get("code", "").strip().upper()
    if scanned == bag["code"]:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "message": "รหัส QR ไม่ตรงกับถุงนี้"}), 400


@app.route("/scan/category", methods=["POST"])
def scan_category():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return redirect(url_for("home"))
    category = request.form.get("category")
    if category not in CATEGORY_LABELS:
        flash("กรุณาเลือกประเภทขยะ")
        return redirect(url_for("scan"))
    conn = db.get_db()
    conn.execute(
        "UPDATE bags SET category = ?, status = 'categorized' WHERE id = ?",
        (category, bag["id"]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("photo"))


# ---------- Photo + confirm ----------
@app.route("/photo")
def photo():
    bag = get_bag(session.get("bag_id"))
    if not bag or not bag["category"]:
        return redirect(url_for("home"))
    return render_template(
        "photo.html", bag=bag, category_label=CATEGORY_LABELS[bag["category"]]
    )


@app.route("/photo/upload", methods=["POST"])
def photo_upload():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return jsonify({"ok": False}), 400

    data_url = request.json.get("image_data")
    note = (request.json.get("note") or "").strip()

    if not data_url:
        return jsonify({"ok": False, "message": "กรุณาถ่ายรูปขยะในถุงก่อน"}), 400

    header, encoded = data_url.split(",", 1)
    image_bytes = base64.b64decode(encoded)
    filename = f"{bag['code']}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    conn = db.get_db()
    conn.execute(
        "UPDATE bags SET photo_path = ?, note = ?, status = 'photographed' WHERE id = ?",
        (f"uploads/{filename}", note, bag["id"]),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "redirect": url_for("waiting_bin")})


# ---------- Waiting for the machine to open + accept the bag ----------
@app.route("/waiting_bin")
def waiting_bin():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return redirect(url_for("home"))
    if bag["status"] not in ("photographed",):
        return redirect(url_for("verify"))
    return render_template("waiting_bin.html", bag=bag)


@app.route("/waiting_bin/status")
def waiting_bin_status():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return jsonify({"ok": False}), 400
    return jsonify({"ok": True, "status": bag["status"]})


# ---------- Verification result + points ----------
@app.route("/verify")
def verify():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return redirect(url_for("home"))
    return render_template(
        "verify.html", bag=bag, category_label=CATEGORY_LABELS.get(bag["category"])
    )


@app.route("/verify/status")
def verify_status():
    bag = get_bag(session.get("bag_id"))
    if not bag:
        return jsonify({"ok": False}), 400
    return jsonify(
        {
            "ok": True,
            "status": bag["status"],
            "ai_result": bag["ai_result"],
            "staff_decision": bag["staff_decision"],
            "points_awarded": bag["points_awarded"],
        }
    )


# ---------- Rewards wallet ----------
@app.route("/rewards")
def rewards():
    user = current_user()
    conn = db.get_db()
    reward_rows = conn.execute("SELECT * FROM rewards ORDER BY cost ASC").fetchall()
    history = conn.execute(
        "SELECT r.name, red.redeemed_at FROM redemptions red "
        "JOIN rewards r ON r.id = red.reward_id WHERE red.user_id = ? "
        "ORDER BY red.id DESC LIMIT 5",
        (user["id"],),
    ).fetchall()
    conn.close()
    return render_template(
        "rewards.html",
        user=user,
        rewards=[dict(r) for r in reward_rows],
        history=[dict(h) for h in history],
    )


@app.route("/rewards/redeem/<int:reward_id>", methods=["POST"])
def redeem_reward(reward_id):
    user = current_user()
    conn = db.get_db()
    reward = conn.execute("SELECT * FROM rewards WHERE id = ?", (reward_id,)).fetchone()
    if reward is None:
        conn.close()
        flash("ไม่พบรางวัลนี้")
        return redirect(url_for("rewards"))
    if user["points"] < reward["cost"]:
        conn.close()
        flash("แต้มสะสมไม่พอสำหรับแลกรางวัลนี้")
        return redirect(url_for("rewards"))

    conn.execute(
        "UPDATE users SET points = points - ? WHERE id = ?", (reward["cost"], user["id"])
    )
    conn.execute(
        "INSERT INTO redemptions (user_id, reward_id) VALUES (?, ?)", (user["id"], reward_id)
    )
    conn.commit()
    conn.close()
    flash(f"แลกรางวัล \"{reward['name']}\" สำเร็จ!")
    return redirect(url_for("rewards"))


# ---------- Profile ----------
@app.route("/profile")
def profile():
    user = current_user()
    conn = db.get_db()
    bags = conn.execute(
        "SELECT * FROM bags WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user["id"],)
    ).fetchall()
    conn.close()
    return render_template(
        "profile.html", user=user, bags=[dict(b) for b in bags], category_labels=CATEGORY_LABELS
    )


if __name__ == "__main__":
    db.init_db()
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "5067"))
    app.run(debug=True, host=host, port=port)
