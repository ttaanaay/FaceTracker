import cv2
import mediapipe as mp
import numpy as np

# =========================
# SETTINGS
# =========================

CAMERA_INDEX = 0
AVATAR_FILE = "avatar.png"

SMOOTHING = 0.25
AVATAR_SCALE = 1.6

# =========================
# LOAD AVATAR
# =========================

avatar = cv2.imread(AVATAR_FILE, cv2.IMREAD_UNCHANGED)

if avatar is None:
    print("ไม่พบไฟล์ avatar.png")
    exit()

# =========================
# MEDIAPIPE
# =========================

mp_face = mp.solutions.face_detection

face_detection = mp_face.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

# =========================
# CAMERA
# =========================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print("ไม่สามารถเปิดกล้องได้")
    exit()

# =========================
# SMOOTH VALUES
# =========================

smooth_x = None
smooth_y = None
smooth_w = None
smooth_h = None


def overlay_png(frame, png, x, y, width, height):

    png = cv2.resize(
        png,
        (width, height),
        interpolation=cv2.INTER_AREA
    )

    h, w = png.shape[:2]

    frame_h, frame_w = frame.shape[:2]

    # Crop boundaries
    x1 = max(0, x)
    y1 = max(0, y)

    x2 = min(frame_w, x + w)
    y2 = min(frame_h, y + h)

    if x1 >= x2 or y1 >= y2:
        return frame

    png_x1 = x1 - x
    png_y1 = y1 - y

    png_x2 = png_x1 + (x2 - x1)
    png_y2 = png_y1 + (y2 - y1)

    cropped_png = png[
        png_y1:png_y2,
        png_x1:png_x2
    ]

    if cropped_png.shape[2] < 4:
        return frame

    alpha = cropped_png[:, :, 3] / 255.0

    for c in range(3):
        frame[y1:y2, x1:x2, c] = (
            alpha * cropped_png[:, :, c]
            + (1 - alpha) *
            frame[y1:y2, x1:x2, c]
        )

    return frame


print("Face Tracker started")
print("กด Q เพื่อออก")

while True:

    success, frame = cap.read()

    if not success:
        break

    # Mirror image
    frame = cv2.flip(frame, 1)

    frame_h, frame_w = frame.shape[:2]

    # MediaPipe ใช้ RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detection.process(rgb)

    if results.detections:

        detection = results.detections[0]

        bbox = detection.location_data.relative_bounding_box

        x = int(bbox.xmin * frame_w)
        y = int(bbox.ymin * frame_h)

        w = int(bbox.width * frame_w)
        h = int(bbox.height * frame_h)

        # เพิ่มขนาด Avatar
        avatar_w = int(w * AVATAR_SCALE)
        avatar_h = int(h * AVATAR_SCALE)

        # Center Avatar
        avatar_x = x + w // 2 - avatar_w // 2
        avatar_y = y + h // 2 - avatar_h // 2

        # =====================
        # SMOOTHING
        # =====================

        if smooth_x is None:

            smooth_x = avatar_x
            smooth_y = avatar_y

            smooth_w = avatar_w
            smooth_h = avatar_h

        else:

            smooth_x = int(
                smooth_x +
                (avatar_x - smooth_x) * SMOOTHING
            )

            smooth_y = int(
                smooth_y +
                (avatar_y - smooth_y) * SMOOTHING
            )

            smooth_w = int(
                smooth_w +
                (avatar_w - smooth_w) * SMOOTHING
            )

            smooth_h = int(
                smooth_h +
                (avatar_h - smooth_h) * SMOOTHING
            )

        # Draw Avatar
        frame = overlay_png(
            frame,
            avatar,
            smooth_x,
            smooth_y,
            smooth_w,
            smooth_h
        )

    cv2.imshow("Face Avatar Tracker", frame)

    key = cv2.waitKey(1)

    if key == ord("q"):
        break


cap.release()

cv2.destroyAllWindows()
