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

# ลอง 0 ก่อน
# ถ้า DroidCam ไม่ขึ้น ลอง 1 หรือ 2
CAMERA_INDEX = 0

# ชื่อไฟล์ Avatar เริ่มต้น (ใช้ตอนกด Cancel ตอนเลือกไฟล์)
AVATAR_FILENAME = "avatar.png"

AVATAR_FILE = os.path.join(
    BASE_PATH,
    AVATAR_FILENAME
)

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
# TKINTER (สำหรับหน้าต่างเลือกไฟล์)
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

    # ตรวจสอบ Alpha Channel

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


print("Face Tracker Starting...")
print("Program Path:")
print(BASE_PATH)

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


def get_avatar_aspect_ratio(img):
    h, w = img.shape[:2]
    return h / w


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
# OPEN CAMERA
# ============================================================

print(
    f"\nกำลังเปิด Camera Index: "
    f"{CAMERA_INDEX}"
)


cap = cv2.VideoCapture(
    CAMERA_INDEX,
    cv2.CAP_DSHOW
)


if not cap.isOpened():

    show_error(
        f"ไม่สามารถเปิดกล้องได้!\n\n"
        f"Camera Index ปัจจุบัน: {CAMERA_INDEX}\n\n"
        f"ลองเปลี่ยน:\n\n"
        f"CAMERA_INDEX = 1\n\n"
        f"หรือ\n\n"
        f"CAMERA_INDEX = 2"
    )


print("Camera Opened Successfully!")


# ============================================================
# CAMERA SETTINGS
# ============================================================

cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    1280
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    720
)

cap.set(
    cv2.CAP_PROP_FPS,
    30
)


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

    # ป้องกันขนาดผิดพลาด

    if width <= 0 or height <= 0:
        return frame


    # Resize Avatar

    resized_png = cv2.resize(
        png,
        (width, height),
        interpolation=cv2.INTER_AREA
    )


    png_h, png_w = resized_png.shape[:2]

    frame_h, frame_w = frame.shape[:2]


    # ============================
    # CALCULATE BOUNDARIES
    # ============================

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


    # Avatar อยู่นอกจอ

    if x1 >= x2 or y1 >= y2:
        return frame


    # ============================
    # PNG CROP
    # ============================

    png_x1 = x1 - x
    png_y1 = y1 - y

    png_x2 = png_x1 + (
        x2 - x1
    )

    png_y2 = png_y1 + (
        y2 - y1
    )


    cropped_png = resized_png[
        png_y1:png_y2,
        png_x1:png_x2
    ]


    # ============================
    # CHECK ALPHA
    # ============================

    if cropped_png.shape[2] < 4:

        # ถ้าไม่มี Alpha Channel
        # วางเป็นภาพปกติ

        frame[
            y1:y2,
            x1:x2
        ] = cropped_png[:, :, :3]

        return frame


    # ============================
    # ALPHA BLENDING
    # ============================

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
        +
        (1.0 - alpha)
        * background
    )


    frame[
        y1:y2,
        x1:x2
    ] = blended.astype(
        np.uint8
    )


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

print(
    f"\nCamera Index: "
    f"{CAMERA_INDEX}"
)

print(
    f"Avatar: "
    f"{current_avatar_path}"
)

print("\n")


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = cap.read()


    if not success:

        print(
            "ไม่สามารถอ่านภาพจากกล้อง"
        )

        break


    # ============================
    # MIRROR CAMERA
    # ============================

    frame = cv2.flip(
        frame,
        1
    )


    frame_h, frame_w = frame.shape[:2]


    # ============================
    # CONVERT TO RGB
    # ============================

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # ============================
    # FACE DETECTION
    # ============================

    results = face_detection.process(
        rgb_frame
    )


    # ============================
    # FACE FOUND
    # ============================

    if (
        results.detections
        and len(results.detections) > 0
    ):

        detection = (
            results.detections[0]
        )


        bbox = (
            detection.location_data
            .relative_bounding_box
        )


        # ========================
        # FACE POSITION
        # ========================

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


        # ========================
        # AVATAR SIZE
        # (คงสัดส่วนภาพของ Avatar เอง
        #  เพื่อไม่ให้ภาพยืด/บิดเบี้ยว)
        # ========================

        avatar_w = int(
            face_w
            * avatar_scale
        )

        avatar_h = int(
            avatar_w
            * avatar_aspect_ratio
        )


        # ========================
        # CENTER AVATAR
        # ========================

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


        # ========================
        # SMOOTHING
        # ========================

        if smooth_x is None:

            smooth_x = avatar_x
            smooth_y = avatar_y

            smooth_w = avatar_w
            smooth_h = avatar_h


        else:

            smooth_x = int(
                smooth_x
                +
                (
                    avatar_x
                    - smooth_x
                )
                * SMOOTHING
            )


            smooth_y = int(
                smooth_y
                +
                (
                    avatar_y
                    - smooth_y
                )
                * SMOOTHING
            )


            smooth_w = int(
                smooth_w
                +
                (
                    avatar_w
                    - smooth_w
                )
                * SMOOTHING
            )


            smooth_h = int(
                smooth_h
                +
                (
                    avatar_h
                    - smooth_h
                )
                * SMOOTHING
            )


        # ========================
        # DRAW AVATAR
        # ========================

        frame = overlay_png(
            frame,
            avatar,
            smooth_x,
            smooth_y,
            smooth_w,
            smooth_h
        )


    # ========================================================
    # ON-SCREEN INFO
    # ========================================================

    info_text = (
        f"Scale: {avatar_scale:.1f}x   "
        f"[+/-] Resize   [O] Change Avatar   [Q] Quit"
    )

    cv2.putText(
        frame,
        info_text,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2,
        cv2.LINE_AA
    )


    # ========================================================
    # SHOW RESULT
    # ========================================================

    cv2.imshow(
        "Face Avatar Tracker",
        frame
    )


    # ========================================================
    # KEYBOARD
    # ========================================================

    key = cv2.waitKey(1) & 0xFF


    if key == ord("q"):

        break


    elif key in (ord("+"), ord("=")):

        avatar_scale = min(
            MAX_AVATAR_SCALE,
            round(avatar_scale + SCALE_STEP, 2)
        )

        print(f"Avatar Scale: {avatar_scale:.1f}x")


    elif key in (ord("-"), ord("_")):

        avatar_scale = max(
            MIN_AVATAR_SCALE,
            round(avatar_scale - SCALE_STEP, 2)
        )

        print(f"Avatar Scale: {avatar_scale:.1f}x")


    elif key in (ord("o"), ord("O")):

        new_path = choose_avatar_file(
            os.path.dirname(current_avatar_path)
        )

        if new_path:

            new_avatar = load_avatar_image(
                new_path,
                exit_on_fail=False
            )

            if new_avatar is not None:

                avatar = new_avatar
                current_avatar_path = new_path
                avatar_aspect_ratio = get_avatar_aspect_ratio(avatar)

                # รีเซ็ต smoothing เพื่อไม่ให้ภาพเก่าค้าง
                smooth_x = None
                smooth_y = None
                smooth_w = None
                smooth_h = None


# ============================================================
# CLEANUP
# ============================================================

print("\nกำลังปิดโปรแกรม...")


cap.release()


face_detection.close()


cv2.destroyAllWindows()

tk_root.destroy()


print("Program Closed")
