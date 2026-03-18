import os
import time
import re
import json
import shutil
from datetime import datetime
from tkinter import Tk, Toplevel, Label, Entry, Button, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# ================= PATHS =================

HOME = os.path.expanduser("~")
DOCUMENTS = os.path.join(HOME, "Documents")

BENCH_ROOT = os.path.join(DOCUMENTS, "Bench_Test")
os.makedirs(BENCH_ROOT, exist_ok=True)

ONEDRIVE = os.environ.get("OneDrive")
PICTURES = os.path.join(ONEDRIVE, "Pictures") if ONEDRIVE and os.path.exists(os.path.join(ONEDRIVE, "Pictures")) else os.path.join(HOME, "Pictures")
SCREENSHOTS = os.path.join(PICTURES, "Screenshots")

if not os.path.exists(SCREENSHOTS):
    SCREENSHOTS = PICTURES

# 🔧 UPDATE DRIVE PATH ONLY
GOOGLE_DRIVE_ROOT = r"G:\My Drive\Profile 1.6"


# ================= STATE =================

TEMP_EXT = (".tmp", ".part", ".crdownload")

handled_files = set()
popup_open_files = set()

active_device = None
pending_screenshot = None


# ================= HELPERS =================

def clean(text):
    return re.sub(r'[\\/:*?"<>|]', '', text.strip().replace(" ", "_"))

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def next_index(folder, device_id):
    return sum(1 for f in os.listdir(folder) if f.startswith(device_id + "_")) + 1

def file_is_stable(path):
    try:
        s1 = os.path.getsize(path)
        time.sleep(1)
        s2 = os.path.getsize(path)
        return s1 == s2
    except:
        return False


# ================= QC STATE =================

def qc_state_path(device_id):
    return os.path.join(BENCH_ROOT, device_id, ".qc_state.json")

def load_state(device_id):
    p = qc_state_path(device_id)
    if not os.path.exists(p):
        return {"uploaded": False, "count": 0}
    with open(p, "r") as f:
        return json.load(f)

def save_state(device_id, count):
    with open(qc_state_path(device_id), "w") as f:
        json.dump({"uploaded": True, "count": count}, f, indent=2)


# ================= TK ROOT =================

app = Tk()
app.withdraw()


# ================= FINISH QC =================

def finish_qc(device_id):

    if not device_id:
        messagebox.showinfo("Finish QC", "No active device.")
        return

    ss_folder = os.path.join(BENCH_ROOT, device_id)

    drive_root = os.path.join(GOOGLE_DRIVE_ROOT, device_id)
    os.makedirs(drive_root, exist_ok=True)

    ss_files = [f for f in os.listdir(ss_folder) if f.lower().endswith(".png")]

    state = load_state(device_id)

    if state["uploaded"] and len(ss_files) == state["count"]:
        messagebox.showinfo("Finish QC", "Drive already up to date.")
        return

    for f in ss_files:
        src = os.path.join(ss_folder, f)
        dst = os.path.join(drive_root, f)

        if not os.path.exists(dst):
            shutil.copy2(src, dst)

    save_state(device_id, len(ss_files))

    messagebox.showinfo("Finish QC", f"{device_id} uploaded successfully.")


# ================= SCREENSHOT POPUP =================

def screenshot_popup(path):

    global active_device, pending_screenshot

    if path in handled_files or path in popup_open_files:
        return

    popup_open_files.add(path)
    pending_screenshot = path

    _, ext = os.path.splitext(path)

    win = Toplevel(app)
    win.title("Bench Test – Screenshot")
    win.geometry("360x230")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    Label(win, text="Device ID (required)").pack(pady=(15,5))

    entry = Entry(win, width=36)
    entry.pack()

    if active_device:
        entry.insert(0, active_device)
        entry.icursor("end")

    entry.focus_force()


    def save_ss():

        global active_device, pending_screenshot

        device = entry.get().strip()

        if not device:
            messagebox.showerror("Error","Device ID required.")
            return

        device_id = clean(device)
        active_device = device_id

        folder = os.path.join(BENCH_ROOT, device_id)
        os.makedirs(folder, exist_ok=True)

        idx = next_index(folder, device_id)

        new_path = os.path.join(
            folder,
            f"{device_id}_{idx}_{timestamp()}{ext}"
        )

        time.sleep(0.5)

        shutil.move(pending_screenshot, new_path)

        handled_files.add(new_path)
        popup_open_files.discard(path)

        pending_screenshot = None

        win.destroy()


    def finish_all():

        if pending_screenshot:
            save_ss()

        finish_qc(active_device)


    entry.bind("<Return>", lambda e: save_ss())

    Button(win, text="Save Screenshot", width=24, command=save_ss).pack(pady=6)

    Button(win, text="Finish QC", width=24, command=finish_all).pack(pady=4)

    Label(
        win,
        text="Designed by Vrijesh",
        font=("Segoe UI",8),
        fg="gray"
    ).pack(side="bottom", pady=6)


# ================= WATCHDOG =================

class ScreenshotHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory or event.src_path.endswith(TEMP_EXT):
            return

        time.sleep(1)

        app.after(0, screenshot_popup, event.src_path)


# ================= BASELINE =================

def init_baseline():

    for r,_,files in os.walk(BENCH_ROOT):
        for f in files:
            handled_files.add(os.path.join(r,f))


# ================= MAIN =================

if __name__ == "__main__":

    init_baseline()

    obs = Observer()

    obs.schedule(
        ScreenshotHandler(),
        SCREENSHOTS,
        recursive=False
    )

    obs.start()

    print("Bench Test QC ACTIVE")
    print("Screenshots → Watchdog")

    try:
        app.mainloop()

    finally:
        obs.stop()
        obs.join()