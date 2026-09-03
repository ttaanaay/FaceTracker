import os
import sys

import cv2
import mediapipe as mp
import numpy as np

import tkinter as tk
from tkinter import filedialog


# ============================================================
# PATH SETTINGS
# ============================================================

def get_base_path():
    """
    คืน path ของโฟลเดอร์โปรแกรม

    - ตอนรัน .py -> โฟลเดอร์ที่มี main.py
    - ตอนรัน .exe -> โฟลเดอร์ที่มี FaceTracker.exe
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()


# ============================================================
# SETTINGS
# ============================================================

# ชื่อไฟล์ Avatar เริ่มต้น (ใช้ตอนกด Cancel ตอนเลือกไฟล์)
AVATAR_FILENAME = "avatar.png"

AVATAR_FILE = os.path.join(
    BASE_PATH,
    AVATAR_FILENAME
)

# ไฟล์จำค่ากล้องที่เลือกไว้ล่าสุด
CAMERA_CONFIG_FILE = os.path.join(
    BASE_PATH,
    "camera_config.txt"
)

# จำนวน index กล้องสูงสุดที่จะไล่เช็ค (กรณีไม่มีชื่ออุปกรณ์)
MAX_CAMERA_TEST = 6

# ความลื่น
# ค่าน้อย = ลื่นขึ้นแต่ตามช้าลง
# ค่าสูง = ตามเร็วขึ้น
SMOOTHING = 0.25

# ขนาด Avatar เริ่มต้น เทียบกับใบหน้า (ปรับได้ตอนรันด้วยปุ่ม +/-)
DEFAULT_AVATAR_SCALE = 1.6

# ขอบเขตขนาดที่ปรับได้
MIN_AVATAR_SCALE = 0.3
MAX_AVATAR_SCALE = 5.0
SCALE_STEP = 0.1


# ============================================================
# ERROR HELPER
# ============================================================

def show_error(message):

    print("\n" + "=" * 60)
    print("ERROR")
    print("=" * 60)
    print(message)
    print("=" * 60)

    input("\nกด Enter เพื่อปิด...")

    sys.exit()


# ============================================================
# TKINTER (สำหรับหน้าต่างเลือกไฟล์ / เลือกกล้อง)
# ============================================================

tk_root = tk.Tk()
tk_root.withdraw()


def choose_avatar_file(initial_dir):
    """
    เปิดหน้าต่างให้เลือกไฟล์ Avatar (PNG)
    คืนค่า path ที่เลือก หรือ None ถ้ากด Cancel
    """

    if not os.path.isdir(initial_dir):
        initial_dir = BASE_PATH

    path = filedialog.askopenfilename(
        parent=tk_root,
        title="เลือกไฟล์ Avatar (PNG พื้นหลังโปร่งใส)",
        initialdir=initial_dir,
        filetypes=[
            ("PNG Files", "*.png"),
            ("All Files", "*.*")
        ]
    )

    tk_root.update()

    return path if path else None


def show_camera_picker(devices, current_index=None):
    """
    แสดงหน้าต่างรายชื่อกล้องให้เลือก
    คืนค่า index ที่เลือก หรือ None ถ้ากด Cancel
    """

    picker = tk.Toplevel(tk_root)
    picker.title("เลือกกล้อง")
    picker.geometry("440x340")
    picker.resizable(False, False)

    label = tk.Label(
        picker,
        text="เลือกกล้องที่ต้องการใช้งาน\n(กล้องมือถือมักขึ้นชื่อว่า DroidCam / IP Webcam / Virtual Camera)",
        font=("Tahoma", 10),
        justify="left"
    )
    label.pack(pady=(12, 6), padx=12, anchor="w")

    listbox = tk.Listbox(
        picker,
        font=("Tahoma", 10),
        width=55,
        height=10
    )
    listbox.pack(padx=12, pady=6, fill="both", expand=True)

    for idx, name in devices:
        listbox.insert("end", f"[{idx}]  {name}")

    if current_index is not None:
        for pos, (idx, name) in enumerate(devices):
            if idx == current_index:
                listbox.selection_set(pos)
                listbox.see(pos)
                break

    selected = {"index": None}

    def on_ok():
        sel = listbox.curselection()
        if sel:
            selected["index"] = devices[sel[0]][0]
        picker.destroy()

    def on_cancel():
        picker.destroy()

    btn_frame = tk.Frame(picker)
    btn_frame.pack(pady=(0, 12))

    ok_btn = tk.Button(btn_frame, text="ตกลง", width=14, command=on_ok)
    ok_btn.pack(side="left", padx=6)

    cancel_btn = tk.Button(btn_frame, text="ยกเลิก", width=14, command=on_cancel)
    cancel_btn.pack(side="left", padx=6)

    listbox.bind("<Double-Button-1>", lambda e: on_ok())

    picker.transient(tk_root)
    picker.grab_set()

    tk_root.wait_window(picker)

    return selected["index"]


# ============================================================
# CAMERA DEVICE LIST
# ============================================================

def list_camera_devices():
    """
    คืนรายชื่อกล้องที่เชื่อมต่อทั้งหมด [(index, name), ...]
    ใช้ pygrabber เพื่อดึงชื่ออุปกรณ์จริง (Windows)
    ถ้าใช้ไม่ได้ จะไล่เช็คทีละ index แทน
    """

    devices = []

    try:
        from pygrabber.dshow_graph import FilterGraph

        graph = FilterGraph()
        names = graph.get_input_devices()

        for idx, name in enumerate(names):
            devices.append((idx, name))

        if devices:
            return devices

    except Exception:
        pass

    print("\nไม่พบรายชื่ออุปกรณ์แบบละเอียด กำลังไล่ตรวจสอบกล้องที่เชื่อมต่อ...")

    for idx in range(MAX_CAMERA_TEST):

        test_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)

        if test_cap.isOpened():
            devices.append((idx, f"กล้อง Index {idx}"))
            test_cap.release()

    return devices


def load_saved_camera_index():

    if os.path.isfile(CAMERA_CONFIG_FILE):

        try:
            with open(CAMERA_CONFIG_FILE, "r") as f:
                return int(f.read().strip())

        except Exception:
            return None

    return None


def save_camera_index(idx):

    try:
        with open(CAMERA_CONFIG_FILE, "w") as f:
            f.write(str(idx))

    except Exception:
        pass


def open_camera(idx):
    """
    เปิดกล้องด้วย index ที่กำหนด พร้อมตั้งค่าความละเอียด
    คืนค่า VideoCapture object หรือ None ถ้าเปิดไม่ได้
    """

    new_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)

    if not new_cap.isOpened():
        return None

    new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    new_cap.set(cv2.CAP_PROP_FPS, 30)

    return new_cap


# ============================================================
# LOAD AVATAR
# ============================================================

def load_avatar_image(path, exit_on_fail=True):
    """
    โหลดและตรวจสอบไฟล์ Avatar
    คืนค่า image ถ้าโหลดสำเร็จ หรือ None ถ้าล้มเหลว (เมื่อ exit_on_fail=False)
    """

    print("\nกำลังโหลด Avatar:")
    print(path)

    img = cv2.imread(
        path,
        cv2.IMREAD_UNCHANGED
    )

    if img is None:

        message = (
            f"ไม่พบไฟล์ Avatar หรือเปิดไฟล์ไม่ได้!\n\n"
            f"{path}"
        )

        if exit_on_fail:
            show_error(message)
        else:
            print("\n" + message)

        return None

    if len(img.shape) < 3:

        message = (
            "ไฟล์ Avatar ไม่ถูกต้อง\n"
            "กรุณาใช้ PNG ที่มีพื้นหลังโปร่งใส"
        )

        if exit_on_fail:
            show_error(message)
        else:
            print("\n" + message)

        return None

    if img.shape[2] != 4:

        print("\nWARNING: PNG ไม่มี Alpha Channel")
        print("แนะนำให้ใช้ PNG พื้นหลังโปร่งใส")

    print("\nAvatar Loaded Successfully!")

    print(
        f"Avatar Size: "
        f"{img.shape[1]} x {img.shape[0]}"
    )

    return img


def get_avatar_aspect_ratio(img):
    h, w = img.shape[:2]
    return h / w


print("Face Tracker Starting...")
print("Program Path:")
print(BASE_PATH)


# ============================================================
# CHOOSE AVATAR
# ============================================================

print("\nกรุณาเลือกไฟล์ Avatar (PNG พื้นหลังโปร่งใส)...")
print("(ถ้ากด Cancel จะใช้ไฟล์ avatar.png เริ่มต้นแทน)")

chosen_avatar_path = choose_avatar_file(BASE_PATH)

if chosen_avatar_path is None:

    print("\nไม่ได้เลือกไฟล์ใหม่ ใช้ไฟล์เริ่มต้น:")
    print(AVATAR_FILE)

    chosen_avatar_path = AVATAR_FILE

avatar = load_avatar_image(
    chosen_avatar_path,
    exit_on_fail=True
)

current_avatar_path = chosen_avatar_path
avatar_aspect_ratio = get_avatar_aspect_ratio(avatar)


# ============================================================
# MEDIAPIPE FACE DETECTION
# ============================================================

print("\nกำลังโหลด Face Detection...")

mp_face_detection = mp.solutions.face_detection

face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

print("Face Detection Loaded Successfully!")


# ============================================================
# CHOOSE CAMERA (มือถือผ่าน DroidCam / IP Webcam ที่ต่อ USB)
# ============================================================

saved_camera_index = load_saved_camera_index()

camera_devices = list_camera_devices()

if not camera_devices:

    show_error(
        "ไม่พบกล้องที่เชื่อมต่อกับคอมพิวเตอร์เลย\n\n"
        "กรุณาตรวจสอบว่า:\n"
        "- เสียบสาย USB เชื่อมมือถือกับคอมแล้ว\n"
        "- เปิดแอป DroidCam / IP Webcam บนมือถือ และตั้งเป็นโหมด USB แล้ว\n"
        "- ติดตั้งโปรแกรม DroidCam Client (หรือโปรแกรมคู่) บนคอมพิวเตอร์แล้ว\n"
        "- อนุญาต USB Debugging บนมือถือ (ถ้าแอปต้องใช้)"
    )

print("\nพบกล้องทั้งหมด:")

for idx, name in camera_devices:
    print(f"  [{idx}]  {name}")

print("\nกรุณาเลือกกล้องที่ต้องการใช้งาน (เลือกกล้องมือถือ เช่น DroidCam)...")

chosen_camera_index = show_camera_picker(
    camera_devices,
    current_index=saved_camera_index
)

if chosen_camera_index is None:

    if saved_camera_index is not None:

        chosen_camera_index = saved_camera_index

        print(
            f"\nไม่ได้เลือกใหม่ ใช้กล้องที่บันทึกไว้ล่าสุด: "
            f"Index {chosen_camera_index}"
        )

    else:

        chosen_camera_index = camera_devices[0][0]

        print(
            f"\nไม่ได้เลือก ใช้กล้องแรกที่พบ: "
            f"Index {chosen_camera_index}"
        )

CAMERA_INDEX = chosen_camera_index

save_camera_index(CAMERA_INDEX)


print(
    f"\nกำลังเปิดกล้อง Index: "
    f"{CAMERA_INDEX}"
)

cap = open_camera(CAMERA_INDEX)

if cap is None:

    show_error(
        f"ไม่สามารถเปิดกล้องที่เลือกได้!\n\n"
        f"Camera Index: {CAMERA_INDEX}\n\n"
        f"ลองปิดโปรแกรมนี้ เปิดแอป DroidCam ใหม่\n"
        f"แล้วเปิดโปรแกรม FaceTracker อีกครั้ง\n"
        f"เพื่อเลือกกล้องใหม่"
    )

print("Camera Opened Successfully!")


# ============================================================
# SMOOTHING VARIABLES
# ============================================================

smooth_x = None
smooth_y = None

smooth_w = None
smooth_h = None


# ============================================================
# RUNTIME STATE (ปรับได้ตอนรันโปรแกรม)
# ============================================================

avatar_scale = DEFAULT_AVATAR_SCALE


# ============================================================
# OVERLAY PNG FUNCTION
# ============================================================

def overlay_png(
    frame,
    png,
    x,
    y,
    width,
    height
):

    if width <= 0 or height <= 0:
        return frame

    resized_png = cv2.resize(
        png,
        (width, height),
        interpolation=cv2.INTER_AREA
    )

    png_h, png_w = resized_png.shape[:2]

    frame_h, frame_w = frame.shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)

    x2 = min(frame_w, x + png_w)
    y2 = min(frame_h, y + png_h)

    if x1 >= x2 or y1 >= y2:
        return frame

    png_x1 = x1 - x
    png_y1 = y1 - y

    png_x2 = png_x1 + (x2 - x1)
    png_y2 = png_y1 + (y2 - y1)

    cropped_png = resized_png[png_y1:png_y2, png_x1:png_x2]

    if cropped_png.shape[2] < 4:

        frame[y1:y2, x1:x2] = cropped_png[:, :, :3]

        return frame

    alpha = cropped_png[:, :, 3] / 255.0

    alpha = alpha[:, :, np.newaxis]

    avatar_rgb = cropped_png[:, :, :3]

    background = frame[y1:y2, x1:x2]

    blended = (
        alpha * avatar_rgb
        + (1.0 - alpha) * background
    )

    frame[y1:y2, x1:x2] = blended.astype(np.uint8)

    return frame


# ============================================================
# START PROGRAM
# ============================================================

print("\n" + "=" * 60)
print("FACE AVATAR TRACKER STARTED")
print("=" * 60)

print("\nControls:")
print("Q       = Exit")
print("+ / -   = ปรับขนาด Avatar")
print("O       = เปลี่ยนรูป Avatar")
print("C       = เปลี่ยนกล้อง")

print(f"\nCamera Index: {CAMERA_INDEX}")
print(f"Avatar: {current_avatar_path}")

print("\n")


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = cap.read()

    if not success:

        print("ไม่สามารถอ่านภาพจากกล้องได้ (กล้องอาจหลุดการเชื่อมต่อ)")
        print("กด C เพื่อเลือกกล้องใหม่ หรือ Q เพื่อออก")

        key = cv2.waitKey(500) & 0xFF

        if key == ord("q"):
            break

        if key in (ord("c"), ord("C")):

            new_devices = list_camera_devices()

            new_index = show_camera_picker(new_devices, current_index=CAMERA_INDEX)

            if new_index is not None:

                new_cap = open_camera(new_index)

                if new_cap is not None:

                    cap.release()
                    cap = new_cap

                    CAMERA_INDEX = new_index
                    save_camera_index(CAMERA_INDEX)

                    print(f"เปลี่ยนกล้องเป็น Index {CAMERA_INDEX}")

        continue


    frame = cv2.flip(frame, 1)

    frame_h, frame_w = frame.shape[:2]

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detection.process(rgb_frame)

    if results.detections and len(results.detections) > 0:

        detection = results.detections[0]

        bbox = detection.location_data.relative_bounding_box

        face_x = int(bbox.xmin * frame_w)
        face_y = int(bbox.ymin * frame_h)

        face_w = int(bbox.width * frame_w)
        face_h = int(bbox.height * frame_h)

        # คงสัดส่วนภาพของ Avatar เอง เพื่อไม่ให้ภาพยืด/บิดเบี้ยว

        avatar_w = int(face_w * avatar_scale)
        avatar_h = int(avatar_w * avatar_aspect_ratio)

        face_center_x = face_x + face_w // 2
        face_center_y = face_y + face_h // 2

        avatar_x = face_center_x - avatar_w // 2
        avatar_y = face_center_y - avatar_h // 2

        if smooth_x is None:

            smooth_x = avatar_x
            smooth_y = avatar_y

            smooth_w = avatar_w
            smooth_h = avatar_h

        else:

            smooth_x = int(smooth_x + (avatar_x - smooth_x) * SMOOTHING)
            smooth_y = int(smooth_y + (avatar_y - smooth_y) * SMOOTHING)

            smooth_w = int(smooth_w + (avatar_w - smooth_w) * SMOOTHING)
            smooth_h = int(smooth_h + (avatar_h - smooth_h) * SMOOTHING)

        frame = overlay_png(
            frame,
            avatar,
            smooth_x,
            smooth_y,
            smooth_w,
            smooth_h
        )

    info_text = (
        f"Scale: {avatar_scale:.1f}x   "
        f"[+/-] Resize   [O] Avatar   [C] Camera   [Q] Quit"
    )

    cv2.putText(
        frame,
        info_text,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 0),
        2,
        cv2.LINE_AA
    )

    cv2.imshow("Face Avatar Tracker", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break

    elif key in (ord("+"), ord("=")):

        avatar_scale = min(MAX_AVATAR_SCALE, round(avatar_scale + SCALE_STEP, 2))

        print(f"Avatar Scale: {avatar_scale:.1f}x")

    elif key in (ord("-"), ord("_")):

        avatar_scale = max(MIN_AVATAR_SCALE, round(avatar_scale - SCALE_STEP, 2))

        print(f"Avatar Scale: {avatar_scale:.1f}x")

    elif key in (ord("o"), ord("O")):

        new_path = choose_avatar_file(os.path.dirname(current_avatar_path))

        if new_path:

            new_avatar = load_avatar_image(new_path, exit_on_fail=False)

            if new_avatar is not None:

                avatar = new_avatar
                current_avatar_path = new_path
                avatar_aspect_ratio = get_avatar_aspect_ratio(avatar)

                smooth_x = None
                smooth_y = None
                smooth_w = None
                smooth_h = None

    elif key in (ord("c"), ord("C")):

        new_devices = list_camera_devices()

        new_index = show_camera_picker(new_devices, current_index=CAMERA_INDEX)

        if new_index is not None and new_index != CAMERA_INDEX:

            new_cap = open_camera(new_index)

            if new_cap is not None:

                cap.release()
                cap = new_cap

                CAMERA_INDEX = new_index
                save_camera_index(CAMERA_INDEX)

                print(f"เปลี่ยนกล้องเป็น Index {CAMERA_INDEX}")

            else:

                print("ไม่สามารถเปิดกล้องที่เลือกได้ ใช้กล้องเดิมต่อไป")


# ============================================================
# CLEANUP
# ============================================================

print("\nกำลังปิดโปรแกรม...")

cap.release()

face_detection.close()

cv2.destroyAllWindows()

tk_root.destroy()

print("Program Closed")
