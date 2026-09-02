import os
import sys

import cv2
import mediapipe as mp
import numpy as np


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

# ชื่อไฟล์ Avatar
AVATAR_FILENAME = "avatar.png"

AVATAR_FILE = os.path.join(
    BASE_PATH,
    AVATAR_FILENAME
)

# ความลื่น
# ค่าน้อย = ลื่นขึ้นแต่ตามช้าลง
# ค่าสูง = ตามเร็วขึ้น
SMOOTHING = 0.25

# ขนาด Avatar เทียบกับใบหน้า
AVATAR_SCALE = 1.6


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
# LOAD AVATAR
# ============================================================

print("Face Tracker Starting...")
print("Program Path:")
print(BASE_PATH)

print("\nกำลังโหลด Avatar:")
print(AVATAR_FILE)


avatar = cv2.imread(
    AVATAR_FILE,
    cv2.IMREAD_UNCHANGED
)


if avatar is None:

    show_error(
        f"ไม่พบไฟล์ Avatar!\n\n"
        f"กรุณานำไฟล์ {AVATAR_FILENAME}\n"
        f"ไปไว้ที่:\n\n"
        f"{BASE_PATH}"
    )


# ตรวจสอบ Alpha Channel

if len(avatar.shape) < 3:

    show_error(
        "ไฟล์ Avatar ไม่ถูกต้อง\n"
        "กรุณาใช้ PNG ที่มีพื้นหลังโปร่งใส"
    )


if avatar.shape[2] != 4:

    print(
        "\nWARNING: PNG ไม่มี Alpha Channel"
    )

    print(
        "แนะนำให้ใช้ PNG พื้นหลังโปร่งใส"
    )


print("\nAvatar Loaded Successfully!")

print(
    f"Avatar Size: "
    f"{avatar.shape[1]} x {avatar.shape[0]}"
)


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
print("Q = Exit")

print(
    f"\nCamera Index: "
    f"{CAMERA_INDEX}"
)

print(
    f"Avatar: "
    f"{AVATAR_FILE}"
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
        # ========================

        avatar_w = int(
            face_w
            * AVATAR_SCALE
        )

        avatar_h = int(
            face_h
            * AVATAR_SCALE
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


# ============================================================
# CLEANUP
# ============================================================

print("\nกำลังปิดโปรแกรม...")


cap.release()


face_detection.close()


cv2.destroyAllWindows()


print("Program Closed")
