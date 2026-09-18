"""Machine app — runs on the PC attached to the smart bin.

Handles the two physical, hardware-tied steps (printing the QR
sticker, opening the bin lid) plus the staff review console. It has
no login/session of its own: it just services whichever bag is next
in the queue, since this simulates a single bin used one bag at a
time. Shares the same SQLite database as client_app.py.
"""
import os
import random

from flask import Flask, render_template, redirect, url_for, flash
import qrcode

import db
from db import CATEGORY_LABELS, BASE_POINTS, DETAIL_BONUS, DETAIL_MIN_LEN, PENALTY_POINTS

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

QR_DIR = os.path.join(app.static_folder, "qrcodes")
os.makedirs(QR_DIR, exist_ok=True)

MACHINE_ID = "#A-12"


def make_qr_image(code):
    img = qrcode.make(code)
    path = os.path.join(QR_DIR, f"{code}.png")
    img.save(path)
    return f"qrcodes/{code}.png"


# ---------- Idle screen: routes to whatever this machine needs to do next ----------
@app.route("/")
def idle():
    printing_bag = db.get_bag_with_status("created")
    if printing_bag:
        return redirect(url_for("print_qr"))
    opening_bag = db.get_bag_with_status("photographed")
    if opening_bag:
        return redirect(url_for("bin_open"))
    return render_template("idle.html", machine_id=MACHINE_ID)


# ---------- Print QR (display only) ----------
# This screen is passive: it just shows the QR for whichever bag is
# waiting. The resident confirms "I've attached it" from their PHONE
# (see client_app.py /waiting_print/confirm), which flips the bag's
# status to 'tagged' — this screen then notices that on its next poll
# and returns to idle by itself. There is no button here.
@app.route("/print_qr")
def print_qr():
    bag = db.get_bag_with_status("created")
    if not bag:
        return redirect(url_for("idle"))
    qr_path = make_qr_image(bag["code"])
    return render_template("print_qr.html", bag=bag, qr_path=qr_path, machine_id=MACHINE_ID)


@app.route("/print_qr/status/<int:bag_id>")
def print_qr_status(bag_id):
    conn = db.get_db()
    bag = conn.execute("SELECT status FROM bags WHERE id = ?", (bag_id,)).fetchone()
    conn.close()
    if bag is None:
        return {"status": None}
    return {"status": bag["status"]}


# ---------- Bin opener ----------
@app.route("/bin_open")
def bin_open():
    bag = db.get_bag_with_status("photographed")
    if not bag:
        return redirect(url_for("idle"))
    return render_template("bin_open.html", bag=bag, machine_id=MACHINE_ID)


@app.route("/bin_open/done/<int:bag_id>", methods=["POST"])
def bin_open_done(bag_id):
    conn = db.get_db()
    bag = conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone()
    if bag is None:
        conn.close()
        return redirect(url_for("idle"))

    ai_result, ai_confidence = run_mock_ai_check()
    conn.execute(
        "UPDATE bags SET status = 'pending_staff', ai_result = ?, ai_confidence = ? WHERE id = ?",
        (ai_result, ai_confidence, bag_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("idle"))


def run_mock_ai_check():
    """Fake AI vision check. In a real system this calls an image
    classification model; here we simulate a confidence score that
    usually (85%) agrees with the category the resident picked."""
    agrees = random.random() < 0.85
    confidence = round(random.uniform(0.78, 0.99) if agrees else random.uniform(0.35, 0.6), 2)
    result = "match" if agrees else "mismatch"
    return result, confidence


# ---------- Staff review console ----------
@app.route("/staff")
def staff_dashboard():
    conn = db.get_db()
    pending = conn.execute(
        "SELECT bags.*, users.name as user_name FROM bags "
        "JOIN users ON users.id = bags.user_id "
        "WHERE bags.status = 'pending_staff' ORDER BY bags.id ASC"
    ).fetchall()
    recent = conn.execute(
        "SELECT bags.*, users.name as user_name FROM bags "
        "JOIN users ON users.id = bags.user_id "
        "WHERE bags.status IN ('verified', 'rejected') ORDER BY bags.id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return render_template(
        "staff.html",
        pending=[dict(p) for p in pending],
        recent=[dict(r) for r in recent],
        category_labels=CATEGORY_LABELS,
    )


@app.route("/staff/<int:bag_id>/confirm", methods=["POST"])
def staff_confirm(bag_id):
    conn = db.get_db()
    bag = conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone()
    if bag is None:
        conn.close()
        return redirect(url_for("staff_dashboard"))
    bag = dict(bag)

    points = compute_points(bag)
    conn.execute(
        "UPDATE bags SET status = 'verified', staff_decision = 'confirmed', points_awarded = ? "
        "WHERE id = ?",
        (points, bag_id),
    )
    conn.execute(
        "UPDATE users SET points = points + ? WHERE id = ?", (points, bag["user_id"])
    )
    conn.commit()
    conn.close()
    flash(f"ยืนยันถุง {bag['code']} แล้ว มอบ {points} แต้ม")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/<int:bag_id>/penalize", methods=["POST"])
def staff_penalize(bag_id):
    conn = db.get_db()
    bag = conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone()
    if bag is None:
        conn.close()
        return redirect(url_for("staff_dashboard"))
    bag = dict(bag)

    penalty = -PENALTY_POINTS
    conn.execute(
        "UPDATE bags SET status = 'rejected', staff_decision = 'penalized', points_awarded = ? "
        "WHERE id = ?",
        (penalty, bag_id),
    )
    conn.execute(
        "UPDATE users SET points = MAX(points + ?, 0), flags = flags + 1 WHERE id = ?",
        (penalty, bag["user_id"]),
    )
    conn.commit()
    conn.close()
    flash(f"ปรับโทษถุง {bag['code']} แล้ว หัก {PENALTY_POINTS} แต้ม")
    return redirect(url_for("staff_dashboard"))


def compute_points(bag):
    base = BASE_POINTS.get(bag["category"], 0)
    bonus = DETAIL_BONUS if bag["note"] and len(bag["note"]) >= DETAIL_MIN_LEN else 0
    return base + bonus


if __name__ == "__main__":
    db.init_db()
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "5069"))
    app.run(debug=True, host=host, port=port)
