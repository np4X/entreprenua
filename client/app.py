"""Static, click-through demo of the resident-facing flow.

This runs entirely in the browser via PyScript (Pyodide/WebAssembly) —
no server, no real database, no real machine. It exists only to show
the screen-by-screen flow on GitHub Pages, matching the same
categories/points rules as the real app (see ../db.py). The actual
working system (client + machine + staff review, shared SQLite DB)
lives in client_app.py / machine_app.py and must be run with Python.
"""
import random
from pyscript import document

CATEGORY_LABELS = {
    "food": "เศษอาหาร",
    "recycle": "รีไซเคิล",
    "general": "ทั่วไป",
}
BASE_POINTS = {"food": 10, "recycle": 15, "general": 5}
DETAIL_BONUS = 5
DETAIL_MIN_LEN = 8
PENALTY_POINTS = 20

CODE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
SCREEN_IDS = [
    "screen-home", "screen-attach", "screen-scan", "screen-photo",
    "screen-bin", "screen-verify", "screen-rewards",
]

state = {
    "points": 1240,
    "bag_code": None,
    "category": None,
    "note": "",
}


def show_screen(name):
    for screen_id in SCREEN_IDS:
        el = document.getElementById(screen_id)
        if screen_id == name:
            el.classList.remove("hidden")
        else:
            el.classList.add("hidden")


def start_bag(event):
    code = "BAG-" + "".join(random.choice(CODE_CHARS) for _ in range(6))
    state["bag_code"] = code
    state["category"] = None
    state["note"] = ""
    document.getElementById("bag-code-display").innerText = code
    show_screen("screen-attach")


def go_to_scan(event):
    document.getElementById("scan-status").classList.add("hidden")
    grid = document.getElementById("category-grid")
    grid.style.opacity = "0.4"
    grid.style.pointerEvents = "none"
    document.getElementById("continue-to-photo-btn").disabled = True
    btns = document.querySelectorAll(".category-btn")
    for i in range(btns.length):
        btns.item(i).classList.remove("selected")
    show_screen("screen-scan")


def simulate_scan(event):
    status = document.getElementById("scan-status")
    status.classList.remove("hidden")
    status.innerText = "✅ สแกนสำเร็จ ตรงกับถุงนี้ เลือกประเภทขยะด้านล่าง"
    grid = document.getElementById("category-grid")
    grid.style.opacity = "1"
    grid.style.pointerEvents = "auto"


def pick_category(event):
    cat = event.currentTarget.getAttribute("data-cat")
    state["category"] = cat
    btns = document.querySelectorAll(".category-btn")
    for i in range(btns.length):
        btns.item(i).classList.remove("selected")
    event.currentTarget.classList.add("selected")
    document.getElementById("continue-to-photo-btn").disabled = False


def go_to_photo(event):
    label = CATEGORY_LABELS.get(state["category"], "-")
    document.getElementById("photo-category-label").innerText = label
    document.getElementById("photo-preview").classList.add("hidden")
    document.getElementById("photo-placeholder").classList.remove("hidden")
    document.getElementById("note-input").value = ""
    document.getElementById("submit-photo-btn").disabled = True
    show_screen("screen-photo")


def submit_photo(event):
    state["note"] = document.getElementById("note-input").value
    document.getElementById("bin-code-text").innerText = (
        f"ใส่ถุง {state['bag_code']} ลงในช่องที่เปิดอยู่"
    )
    show_screen("screen-bin")


def throw_done(event):
    ai_ok = random.random() < 0.85
    staff_ok = ai_ok or random.random() < 0.2

    ai_icon = document.getElementById("ai-icon")
    ai_desc = document.getElementById("ai-desc")
    if ai_ok:
        ai_icon.className = "icon-badge ok"
        ai_icon.innerText = "✓"
        ai_desc.innerText = f'ตรงกับ "{CATEGORY_LABELS.get(state["category"])}" ที่เลือกไว้'
    else:
        ai_icon.className = "icon-badge fail"
        ai_icon.innerText = "!"
        ai_desc.innerText = "รูปอาจไม่ตรงกับประเภทที่เลือกไว้"

    staff_icon = document.getElementById("staff-icon")
    staff_title = document.getElementById("staff-title")
    staff_desc = document.getElementById("staff-desc")

    if staff_ok:
        points = BASE_POINTS.get(state["category"], 0)
        if state["note"] and len(state["note"]) >= DETAIL_MIN_LEN:
            points += DETAIL_BONUS
        staff_icon.className = "icon-badge ok"
        staff_icon.innerText = "✓"
        staff_title.innerText = "พนักงานยืนยันแล้ว"
        staff_desc.innerText = "ตรวจสอบผ่าน"
    else:
        points = -PENALTY_POINTS
        staff_icon.className = "icon-badge fail"
        staff_icon.innerText = "✕"
        staff_title.innerText = "พนักงานพบว่าข้อมูลไม่ตรง"
        staff_desc.innerText = "ถูกหักแต้มเนื่องจากแยกผิด/ให้ข้อมูลเท็จ"

    state["points"] = max(state["points"] + points, 0)
    document.getElementById("points-display").innerText = f"{state['points']:,}"

    sign = "+" if points >= 0 else ""
    document.getElementById("points-earned-text").innerText = f"{sign}{points} แต้ม"

    label = CATEGORY_LABELS.get(state["category"], "-")
    document.getElementById("last-activity-text").innerText = (
        f"เมื่อสักครู่ · {label} · ได้ {points} แต้ม"
    )

    show_screen("screen-verify")


def refresh_reward_buttons():
    for i in range(4):
        btn = document.getElementById(f"redeem-{i}")
        cost = int(btn.getAttribute("data-cost"))
        btn.disabled = state["points"] < cost


def go_to_rewards(event):
    document.getElementById("rewards-points-display").innerText = f"{state['points']:,}"
    refresh_reward_buttons()
    show_screen("screen-rewards")


def redeem_click(event):
    btn = event.currentTarget
    cost = int(btn.getAttribute("data-cost"))
    if state["points"] >= cost:
        state["points"] -= cost
        document.getElementById("rewards-points-display").innerText = f"{state['points']:,}"
        document.getElementById("points-display").innerText = f"{state['points']:,}"
        refresh_reward_buttons()


def go_home(event):
    show_screen("screen-home")


# Boot: PyScript is ready once this module runs, so swap the loading
# message for the actual app.
document.getElementById("loading").classList.add("hidden")
document.getElementById("app").classList.remove("hidden")
show_screen("screen-home")
