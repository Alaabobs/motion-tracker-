"""
motion_cam.py — Motion-Activated Webcam
Detects motion via frame differencing, saves timestamped video clips,
and optionally sends email alerts.

Dependencies: pip install opencv-python python-dotenv
"""

import cv2
import os
import time
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load .env if it exists (for email credentials). Falls back silently if
# python-dotenv isn't installed — email alerts just won't work without creds.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─────────────────────────────────────────
#  CONFIG — tweak these to your liking
# ─────────────────────────────────────────
MOTION_THRESHOLD   = 5000    # min contour area (pixels²) to count as motion
BLUR_SIZE          = 21      # gaussian blur kernel (must be odd)
DILATE_ITERATIONS  = 2       # how much to expand detected blobs
COOLDOWN_SECONDS   = 3       # pause between triggering new clips
CLIP_DURATION      = 10      # seconds to record after motion detected
OUTPUT_DIR         = os.getenv("MOTION_OUTPUT_DIR", "clips")  # where video clips are saved
DRAW_BOXES         = True    # draw green boxes around motion areas

# Email alert config — pulled from environment so credentials never end up in git.
# Set SEND_EMAIL=true in your .env to enable. Use a Gmail App Password, not your real password.
SEND_EMAIL    = os.getenv("SEND_EMAIL", "false").lower() == "true"
EMAIL_SENDER  = os.getenv("EMAIL_SENDER", "")
EMAIL_PASS    = os.getenv("EMAIL_PASS", "")
EMAIL_TARGET  = os.getenv("EMAIL_TARGET", "")
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))


# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def timestamp_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def send_alert_email(clip_path: str):
    """Fire-and-forget email alert in a background thread."""
    if not (EMAIL_SENDER and EMAIL_PASS and EMAIL_TARGET):
        print("[EMAIL] Skipped — credentials not set in .env")
        return

    def _send():
        try:
            msg = MIMEMultipart()
            msg["From"]    = EMAIL_SENDER
            msg["To"]      = EMAIL_TARGET
            msg["Subject"] = "Motion Detected"
            body = f"Motion was detected at {datetime.now().strftime('%H:%M:%S on %d %b %Y')}.\nClip saved to: {clip_path}"
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASS)
                server.sendmail(EMAIL_SENDER, EMAIL_TARGET, msg.as_string())
            print("[EMAIL] Alert sent.")
        except Exception as e:
            print(f"[EMAIL] Failed to send: {e}")

    threading.Thread(target=_send, daemon=True).start()


def get_video_writer(path: str, fps: float, frame_size: tuple):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, frame_size)


# ─────────────────────────────────────────
#  MOTION DETECTOR
# ─────────────────────────────────────────
class MotionDetector:
    def __init__(self):
        self.prev_gray = None

    def detect(self, frame) -> tuple[bool, list]:
        """
        Returns (motion_detected, contours).
        Uses frame differencing + threshold + dilation.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (BLUR_SIZE, BLUR_SIZE), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return False, []

        diff  = cv2.absdiff(self.prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=DILATE_ITERATIONS)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.prev_gray = gray

        significant = [c for c in contours if cv2.contourArea(c) > MOTION_THRESHOLD]
        return len(significant) > 0, significant


# ─────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────
def run():
    ensure_output_dir()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Cannot open webcam. Check that it's connected and not in use.")
        return

    fps         = cap.get(cv2.CAP_PROP_FPS) or 20.0
    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size  = (width, height)

    detector    = MotionDetector()
    writer      = None
    recording   = False
    clip_end    = 0
    last_motion = 0

    print("[INFO] Motion Cam running. Press Q to quit.")
    print(f"[INFO] Clips will be saved to ./{OUTPUT_DIR}/")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[ERROR] Failed to grab frame.")
            break

        now = time.time()
        motion_found, contours = detector.detect(frame)

        # ── Draw boxes around motion blobs ──
        if DRAW_BOXES and motion_found:
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 80), 2)

        # ── Trigger new recording ──
        if motion_found and not recording and (now - last_motion > COOLDOWN_SECONDS):
            ts       = timestamp_str()
            clip_path = os.path.join(OUTPUT_DIR, f"motion_{ts}.mp4")
            writer   = get_video_writer(clip_path, fps, frame_size)
            recording = True
            clip_end  = now + CLIP_DURATION
            last_motion = now
            print(f"[MOTION] Detected — recording to {clip_path}")

            if SEND_EMAIL:
                send_alert_email(clip_path)

        # ── Write frame to clip ──
        if recording:
            writer.write(frame)
            remaining = max(0, clip_end - now)
            cv2.putText(frame, f"REC  {remaining:.1f}s", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 60, 255), 2)

            if now >= clip_end:
                writer.release()
                writer    = None
                recording = False
                print("[INFO] Clip saved.")

        # ── Status overlay ──
        status = "MOTION" if motion_found else "Watching..."
        color  = (0, 255, 80) if motion_found else (180, 180, 180)
        cv2.putText(frame, status, (10, height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        cv2.imshow("Motion Cam — press Q to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    if writer:
        writer.release()
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Shutting down.")


if __name__ == "__main__":
    run()
