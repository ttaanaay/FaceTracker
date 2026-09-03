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

AVATAR_FILENAME = "avatar.png"

AVATAR_FILE = os.path.join(
    BASE_PATH,
    AVATAR_FILENAME
)

CAMERA_CONFIG_FILE = os.path.join(
    BASE_PATH,
    "camera_config.txt"
)

MAX_CAMERA_TEST = 6

SMOOTHING = 0.25

DEFAULT_AVATAR_SCALE = 1.6

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
# TKINTER
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
    Popup เลือกกล้องสำหรับ Windows

    แก้ปัญหา:
    1. Console แย่ง focus ทำให้ popup พิมพ์ไม่ได้
    2. กดเลข [index] แล้วเลือกกล้องทันทีโดยไม่ต้องใช้เมาส์

    ตัวอย่าง:
        [0] USB2.0 VGA UVC WebCam
        [1] DroidCam Video
        [2] OBS Virtual Camera

    กด 1 -> เลือก DroidCam Video ทันที
    Enter -> เลือกรายการที่ highlight
    Esc -> ยกเลิก
    """

    import ctypes

    picker = tk.Toplevel(tk_root)
    picker.title("เลือกกล้อง")
    picker.geometry("440x340")
    picker.resizable(False, False)

    # --------------------------------------------------------
    # สร้าง UI ก่อน เพื่อให้ได้ HWND ที่พร้อมใช้งาน
    # --------------------------------------------------------

    label = tk.Label(
        picker,
        text="เลือกกล้องที่ต้องการใช้งาน\n"
             "(กดเลขใน [ ] เพื่อเลือกทันที ไม่ต้องคลิก)",
        font=("Tahoma", 10),
        justify="left"
    )
    label.pack(pady=(12, 6), padx=12, anchor="w")

    listbox = tk.Listbox(
        picker,
        font=("Tahoma", 10),
        width=55,
        height=10,
        takefocus=True
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
    closed = {"value": False}

    def finish_with_index(camera_index):
        """เลือกกล้องตามเลขใน [ ] และปิด popup ทันที"""

        if closed["value"]:
            return True

        for pos, (idx, name) in enumerate(devices):
            if idx == camera_index:
                selected["index"] = idx

                try:
                    listbox.selection_clear(0, "end")
                    listbox.selection_set(pos)
                    listbox.see(pos)
                except tk.TclError:
                    pass

                closed["value"] = True
                picker.destroy()
                return True

        return False

    def on_ok(event=None):
        if closed["value"]:
            return "break"

        sel = listbox.curselection()

        if sel:
            selected["index"] = devices[sel[0]][0]

        closed["value"] = True
        picker.destroy()
        return "break"

    def on_cancel(event=None):
        if not closed["value"]:
            closed["value"] = True
            picker.destroy()

        return "break"

    def on_key(event):
        """
        รับคีย์จากทุก child widget ใน popup

        สำคัญ:
        bind ที่ Toplevel อย่างเดียวอาจไม่ทำงานตามที่คาด
        เมื่อ focus อยู่บน Listbox/Button
        จึงใช้ bind_all ระหว่างที่ popup เปิดอยู่
        """

        key = event.keysym

        # ตัวเลขแถวบน keyboard: 0-9
        # และ Numpad: KP_0 ... KP_9
        if key.startswith("KP_"):
            key = key[3:]

        if len(key) == 1 and key.isdigit():
            camera_index = int(key)

            if finish_with_index(camera_index):
                return "break"

        if key in ("Return", "KP_Enter"):
            return on_ok(event)

        if key == "Escape":
            return on_cancel(event)

        return None

    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    btn_frame = tk.Frame(picker)
    btn_frame.pack(pady=(0, 12))

    ok_btn = tk.Button(
        btn_frame,
        text="ตกลง",
        width=14,
        command=on_ok
    )
    ok_btn.pack(side="left", padx=6)

    cancel_btn = tk.Button(
        btn_frame,
        text="ยกเลิก",
        width=14,
        command=on_cancel
    )
    cancel_btn.pack(side="left", padx=6)

    listbox.bind(
        "<Double-Button-1>",
        on_ok
    )

    # --------------------------------------------------------
    # Keyboard
    # --------------------------------------------------------

    # ใช้ bind_all เพื่อให้เลขทำงานแม้ focus อยู่ที่ Listbox/Button
    bind_id = picker.bind_all(
        "<KeyPress>",
        on_key,
        add="+"
    )

    # --------------------------------------------------------
    # Windows Focus Fix
    # --------------------------------------------------------

    picker.transient(tk_root)

    # ทำให้เป็น modal
    try:
        picker.grab_set()
    except tk.TclError:
        pass

    # ให้ Tk สร้าง HWND ก่อน
    picker.update_idletasks()

    hwnd = picker.winfo_id()

    def force_windows_foreground():
        """
        ใช้ Win32 API โดยตรง

        Tk focus_force/lift อย่างเดียวไม่พอในบางกรณี
        โดยเฉพาะเมื่อ EXE มี Console window เป็น foreground
        """

        try:
            if closed["value"] or not picker.winfo_exists():
                return

            picker.deiconify()
            picker.update_idletasks()

            hwnd_local = picker.winfo_id()

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            HWND_TOPMOST = -1
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040

            # 1) เอา popup ขึ้นบนสุด
            user32.SetWindowPos(
                hwnd_local,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
            )

            # 2) เอาขึ้นด้านหน้า
            user32.BringWindowToTop(hwnd_local)

            # 3) บังคับให้เป็น foreground window
            foreground_hwnd = user32.GetForegroundWindow()

            current_thread = kernel32.GetCurrentThreadId()

            if foreground_hwnd:
                foreground_thread = user32.GetWindowThreadProcessId(
                    foreground_hwnd,
                    None
                )

                if foreground_thread != current_thread:
                    # Windows อาจ block SetForegroundWindow
                    # จึง attach input thread ชั่วคราว
                    attached = user32.AttachThreadInput(
                        foreground_thread,
                        current_thread,
                        True
                    )

                    try:
                        user32.SetForegroundWindow(hwnd_local)
                        user32.SetActiveWindow(hwnd_local)
                    finally:
                        if attached:
                            user32.AttachThreadInput(
                                foreground_thread,
                                current_thread,
                                False
                            )
                else:
                    user32.SetForegroundWindow(hwnd_local)
                    user32.SetActiveWindow(hwnd_local)

            # 4) Tk focus อีกชั้น
            picker.lift()
            picker.focus_force()
            listbox.focus_set()

        except Exception:
            # fallback สำหรับกรณีที่ Win32 API ใช้ไม่ได้
            try:
                picker.lift()
                picker.attributes("-topmost", True)
                picker.focus_force()
                listbox.focus_set()
            except Exception:
                pass

    # --------------------------------------------------------
    # บังคับ focus หลายครั้ง
    # --------------------------------------------------------

    picker.after(0, force_windows_foreground)
    picker.after(50, force_windows_foreground)
    picker.after(150, force_windows_foreground)
    picker.after(350, force_windows_foreground)
    picker.after(700, force_windows_foreground)

    # ตอนเปิด popup ให้ keyboard พร้อมใช้งานทันที
    picker.after(100, listbox.focus_set)

    try:
        tk_root.wait_window(picker)
    finally:
        # ล้าง bind_all เมื่อ popup ปิด
        try:
            tk_root.unbind_all(
                "<KeyPress>",
                bind_id
            )
        except Exception:
            pass

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

        test_cap = cv2.VideoCapture(
            idx,
            cv2.CAP_DSHOW
        )

        if test_cap.isOpened():

            devices.append(
                (idx, f"กล้อง Index {idx}")
            )

            test_cap.release()

    return devices


def load_saved_camera_index():

    if os.path.isfile(CAMERA_CONFIG_FILE):

        try:

            with open(
                CAMERA_CONFIG_FILE,
                "r"
            ) as f:

                return int(
                    f.read().strip()
                )

        except Exception:
            return None

    return None


def save_camera_index(idx):

    try:

        with open(
            CAMERA_CONFIG_FILE,
            "w"
        ) as f:

            f.write(str(idx))

    except Exception:
        pass


def open_camera(idx):
    """
    เปิดกล้อง Windows แบบปลอดภัยสำหรับทั้งกล้องปกติและ Virtual Camera

    ปัญหาของ DroidCam บางรุ่น:
    - DirectShow เปิด device ไม่ได้
    - Media Foundation เปิดได้ แต่ stream ไม่รองรับการบังคับ
      1280x720 หลังเปิด ทำให้ cap.read() ภายหลัง crash ใน OpenCV

    ดังนั้น:
    - เปิดกล้องก่อน
    - อ่าน frame จริงเพื่อยืนยัน
    - ไม่บังคับ resolution ของ Virtual Camera
    - ใช้ resolution ที่ device ส่งมาเอง
    """

    backends = [
        ("DirectShow", cv2.CAP_DSHOW),
        ("Media Foundation", cv2.CAP_MSMF),
        ("Default", cv2.CAP_ANY),
    ]

    for backend_name, backend in backends:

        print(
            f"กำลังเปิดกล้อง Index {idx} "
            f"ด้วย {backend_name}..."
        )

        new_cap = None

        try:
            new_cap = cv2.VideoCapture(
                idx,
                backend
            )

            if not new_cap.isOpened():
                print(
                    f"{backend_name} ไม่สามารถเปิด device ได้"
                )
                if new_cap is not None:
                    new_cap.release()
                continue

            # อ่าน frame จริงก่อนทำอะไรกับ stream
            ok, test_frame = new_cap.read()

            if not ok or test_frame is None:
                print(
                    f"{backend_name} เปิด device ได้ "
                    f"แต่ไม่สามารถอ่าน frame ได้"
                )
                new_cap.release()
                continue

            # ตรวจสอบ frame ป้องกัน OpenCV crash จาก Mat ที่ผิดปกติ
            if (
                not hasattr(test_frame, "shape")
                or len(test_frame.shape) != 3
                or test_frame.shape[0] <= 0
                or test_frame.shape[1] <= 0
                or test_frame.shape[2] < 3
            ):
                print(
                    f"{backend_name} ส่ง frame ที่ไม่ถูกต้อง: "
                    f"{getattr(test_frame, 'shape', None)}"
                )
                new_cap.release()
                continue

            # ทำให้ numpy buffer เป็น contiguous
            test_frame = np.ascontiguousarray(test_frame)

            actual_h, actual_w = test_frame.shape[:2]

            print(
                f"เปิดกล้องสำเร็จด้วย {backend_name} "
                f"({actual_w}x{actual_h})"
            )

            # สำคัญ: ไม่บังคับ 1280x720
            # เพราะ DroidCam/Virtual Camera บาง driver
            # จะทำให้ stream พังหลังเปลี่ยน resolution

            return new_cap

        except cv2.error as e:

            print(
                f"{backend_name} OpenCV error: {e}"
            )

        except Exception as e:

            print(
                f"{backend_name} error: {e}"
            )

        finally:

            if new_cap is not None:

                try:
                    if not new_cap.isOpened():
                        new_cap.release()
                except Exception:
                    pass

    return None


# ============================================================
# LOAD AVATAR
# ============================================================

def load_avatar_image(
    path,
    exit_on_fail=True
):
    """
    โหลดและตรวจสอบไฟล์ Avatar
    คืนค่า image ถ้าโหลดสำเร็จ หรือ None ถ้าล้มเหลว
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

print(
    "\nกรุณาเลือกไฟล์ Avatar "
    "(PNG พื้นหลังโปร่งใส)..."
)

print(
    "(ถ้ากด Cancel จะใช้ไฟล์ "
    "avatar.png เริ่มต้นแทน)"
)

chosen_avatar_path = choose_avatar_file(
    BASE_PATH
)

if chosen_avatar_path is None:

    print(
        "\nไม่ได้เลือกไฟล์ใหม่ "
        "ใช้ไฟล์เริ่มต้น:"
    )

    print(AVATAR_FILE)

    chosen_avatar_path = AVATAR_FILE


avatar = load_avatar_image(
    chosen_avatar_path,
    exit_on_fail=True
)

current_avatar_path = chosen_avatar_path

avatar_aspect_ratio = get_avatar_aspect_ratio(
    avatar
)


# ============================================================
# MEDIAPIPE FACE DETECTION
# ============================================================

print(
    "\nกำลังโหลด Face Detection..."
)

mp_face_detection = mp.solutions.face_detection

face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

print(
    "Face Detection Loaded Successfully!"
)


# ============================================================
# CHOOSE CAMERA
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

    print(
        f"  [{idx}]  {name}"
    )


print(
    "\nกรุณาเลือกกล้องที่ต้องการใช้งาน "
    "(เลือกกล้องมือถือ เช่น DroidCam)..."
)

chosen_camera_index = show_camera_picker(
    camera_devices,
    current_index=saved_camera_index
)


if chosen_camera_index is None:

    if saved_camera_index is not None:

        chosen_camera_index = saved_camera_index

        print(
            f"\nไม่ได้เลือกใหม่ "
            f"ใช้กล้องที่บันทึกไว้ล่าสุด: "
            f"Index {chosen_camera_index}"
        )

    else:

        chosen_camera_index = camera_devices[0][0]

        print(
            f"\nไม่ได้เลือก "
            f"ใช้กล้องแรกที่พบ: "
            f"Index {chosen_camera_index}"
        )


CAMERA_INDEX = chosen_camera_index

save_camera_index(
    CAMERA_INDEX
)


print(
    f"\nกำลังเปิดกล้อง Index: "
    f"{CAMERA_INDEX}"
)

cap = open_camera(
    CAMERA_INDEX
)


if cap is None:

    show_error(
        f"ไม่สามารถเปิดกล้องที่เลือกได้!\n\n"
        f"Camera Index: {CAMERA_INDEX}\n\n"
        f"ลองปิดโปรแกรมนี้ เปิดแอป DroidCam ใหม่\n"
        f"แล้วเปิดโปรแกรม FaceTracker อีกครั้ง\n"
        f"เพื่อเลือกกล้องใหม่"
    )


print(
    "Camera Opened Successfully!"
)


# ============================================================
# SMOOTHING VARIABLES
# ============================================================

smooth_x = None
smooth_y = None

smooth_w = None
smooth_h = None


# ============================================================
# RUNTIME STATE
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

    x2 = min(
        frame_w,
        x + png_w
    )

    y2 = min(
        frame_h,
        y + png_h
    )

    if x1 >= x2 or y1 >= y2:
        return frame

    png_x1 = x1 - x
    png_y1 = y1 - y

    png_x2 = (
        png_x1
        + (x2 - x1)
    )

    png_y2 = (
        png_y1
        + (y2 - y1)
    )

    cropped_png = resized_png[
        png_y1:png_y2,
        png_x1:png_x2
    ]

    if cropped_png.shape[2] < 4:

        frame[
            y1:y2,
            x1:x2
        ] = cropped_png[:, :, :3]

        return frame

    alpha = (
        cropped_png[:, :, 3]
        / 255.0
    )

    alpha = alpha[:, :, np.newaxis]

    avatar_rgb = cropped_png[:, :, :3]

    background = frame[
        y1:y2,
        x1:x2
    ]

    blended = (
        alpha * avatar_rgb
        + (1.0 - alpha) * background
    )

    frame[
        y1:y2,
        x1:x2
    ] = blended.astype(np.uint8)

    return frame


# ============================================================
# START PROGRAM
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "FACE AVATAR TRACKER STARTED"
)

print(
    "=" * 60
)


print("\nControls:")

print("Q       = Exit")
print("+ / -   = ปรับขนาด Avatar")
print("O       = เปลี่ยนรูป Avatar")
print("C       = เปลี่ยนกล้อง")

print(
    f"\nCamera Index: {CAMERA_INDEX}"
)

print(
    f"Avatar: {current_avatar_path}"
)

print("\n")


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:
        success, frame = cap.read()

        if success and frame is not None:
            # ป้องกัน OpenCV error จาก buffer/stride ของบาง virtual camera
            frame = np.ascontiguousarray(frame)

    except cv2.error as e:

        print(
            f"OpenCV ไม่สามารถอ่านภาพจากกล้องได้: {e}"
        )

        success = False
        frame = None

    except Exception as e:

        print(
            f"เกิดข้อผิดพลาดขณะอ่านกล้อง: {e}"
        )

        success = False
        frame = None

    if not success or frame is None:

        print(
            "ไม่สามารถอ่านภาพจากกล้องได้ "
            "(กล้องอาจหลุดการเชื่อมต่อหรือ driver มีปัญหา)"
        )

        print(
            "กด C เพื่อเลือกกล้องใหม่ "
            "หรือ Q เพื่อออก"
        )

        key = cv2.waitKey(500) & 0xFF

        if key == ord("q"):
            break

        if key in (
            ord("c"),
            ord("C")
        ):

            new_devices = list_camera_devices()

            new_index = show_camera_picker(
                new_devices,
                current_index=CAMERA_INDEX
            )

            if new_index is not None:

                new_cap = open_camera(
                    new_index
                )

                if new_cap is not None:

                    cap.release()

                    cap = new_cap

                    CAMERA_INDEX = new_index

                    save_camera_index(
                        CAMERA_INDEX
                    )

                    print(
                        f"เปลี่ยนกล้องเป็น "
                        f"Index {CAMERA_INDEX}"
                    )

        continue


    frame = cv2.flip(
        frame,
        1
    )

    frame_h, frame_w = frame.shape[:2]

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = face_detection.process(
        rgb_frame
    )

    if (
        results.detections
        and len(results.detections) > 0
    ):

        detection = results.detections[0]

        bbox = (
            detection
            .location_data
            .relative_bounding_box
        )

        face_x = int(
            bbox.xmin * frame_w
        )

        face_y = int(
            bbox.ymin * frame_h
        )

        face_w = int(
            bbox.width * frame_w
        )

        face_h = int(
            bbox.height * frame_h
        )

        avatar_w = int(
            face_w * avatar_scale
        )

        avatar_h = int(
            avatar_w
            * avatar_aspect_ratio
        )

        face_center_x = (
            face_x
            + face_w // 2
        )

        face_center_y = (
            face_y
            + face_h // 2
        )

        avatar_x = (
            face_center_x
            - avatar_w // 2
        )

        avatar_y = (
            face_center_y
            - avatar_h // 2
        )

        if smooth_x is None:

            smooth_x = avatar_x
            smooth_y = avatar_y

            smooth_w = avatar_w
            smooth_h = avatar_h

        else:

            smooth_x = int(
                smooth_x
                + (
                    avatar_x
                    - smooth_x
                )
                * SMOOTHING
            )

            smooth_y = int(
                smooth_y
                + (
                    avatar_y
                    - smooth_y
                )
                * SMOOTHING
            )

            smooth_w = int(
                smooth_w
                + (
                    avatar_w
                    - smooth_w
                )
                * SMOOTHING
            )

            smooth_h = int(
                smooth_h
                + (
                    avatar_h
                    - smooth_h
                )
                * SMOOTHING
            )

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
        f"[+/-] Resize   "
        f"[O] Avatar   "
        f"[C] Camera   "
        f"[Q] Quit"
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

    cv2.imshow(
        "Face Avatar Tracker",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key in (
        ord("+"),
        ord("=")
    ):

        avatar_scale = min(
            MAX_AVATAR_SCALE,
            round(
                avatar_scale
                + SCALE_STEP,
                2
            )
        )

        print(
            f"Avatar Scale: "
            f"{avatar_scale:.1f}x"
        )

    elif key in (
        ord("-"),
        ord("_")
    ):

        avatar_scale = max(
            MIN_AVATAR_SCALE,
            round(
                avatar_scale
                - SCALE_STEP,
                2
            )
        )

        print(
            f"Avatar Scale: "
            f"{avatar_scale:.1f}x"
        )

    elif key in (
        ord("o"),
        ord("O")
    ):

        new_path = choose_avatar_file(
            os.path.dirname(
                current_avatar_path
            )
        )

        if new_path:

            new_avatar = load_avatar_image(
                new_path,
                exit_on_fail=False
            )

            if new_avatar is not None:

                avatar = new_avatar

                current_avatar_path = new_path

                avatar_aspect_ratio = (
                    get_avatar_aspect_ratio(
                        avatar
                    )
                )

                smooth_x = None
                smooth_y = None
                smooth_w = None
                smooth_h = None

    elif key in (
        ord("c"),
        ord("C")
    ):

        new_devices = list_camera_devices()

        new_index = show_camera_picker(
            new_devices,
            current_index=CAMERA_INDEX
        )

        if (
            new_index is not None
            and new_index != CAMERA_INDEX
        ):

            new_cap = open_camera(
                new_index
            )

            if new_cap is not None:

                cap.release()

                cap = new_cap

                CAMERA_INDEX = new_index

                save_camera_index(
                    CAMERA_INDEX
                )

                print(
                    f"เปลี่ยนกล้องเป็น "
                    f"Index {CAMERA_INDEX}"
                )

            else:

                print(
                    "ไม่สามารถเปิดกล้องที่เลือกได้ "
                    "ใช้กล้องเดิมต่อไป"
                )


# ============================================================
# CLEANUP
# ============================================================

print(
    "\nกำลังปิดโปรแกรม..."
)

cap.release()

face_detection.close()

cv2.destroyAllWindows()

tk_root.destroy()

print(
    "Program Closed"
)
