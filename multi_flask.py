# multi_view_cam.py
import cv2, time, threading
from flask import Flask, Response, render_template_string

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Multi-Viewer Camera</title>
    <style>
      body { margin:0; background:#0b0b0b; color:#ddd; font-family:sans-serif;
             display:flex; align-items:center; justify-content:center; height:100vh; }
      main { text-align:center; }
      img { max-width:95vw; max-height:85vh; border-radius:12px; box-shadow:0 8px 30px rgba(0,0,0,.6); }
      p { opacity:.7; margin-top:10px; font-size:14px }
    </style>
  </head>
  <body>
    <main>
      <img src="/video" alt="camera stream" />
      <p>Open this page on multiple devices—everyone sees the same feed.</p>
    </main>
  </body>
</html>
"""

# Shared state for all clients
latest_jpeg = None          # bytes of the most recent JPEG
frame_id = 0                # monotonically increasing counter
cond = threading.Condition()  # notify clients when a new frame arrives
running = True

def camera_loop(cam_index=0, target_fps=20, width=None, height=None, jpeg_quality=80):
    """Grab frames, encode once as JPEG, and publish to all clients."""
    global latest_jpeg, frame_id, running
    cap = cv2.VideoCapture(cam_index)
    if width:  cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    if height: cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        print("[ERR] Could not open camera"); return

    frame_interval = 1.0 / max(1, target_fps)
    next_t = time.time()

    while running:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05); continue

        # Optional selfie flip:
        # frame = cv2.flip(frame, 1)

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
        if not ok:
            continue
        jpg = buf.tobytes()

        with cond:
            latest_jpeg = jpg
            frame_id_plus_one = frame_id + 1
            # Avoid rollover issues in wait_for lambdas
            frame_id = frame_id_plus_one
            cond.notify_all()

        # simple FPS cap
        next_t += frame_interval
        sleep = next_t - time.time()
        if sleep > 0:
            time.sleep(sleep)
        else:
            next_t = time.time()

    cap.release()

def mjpeg_generator():
    """Per-client generator that yields the newest available JPEG frames."""
    last_seen = -1
    # Send something quickly after client connects
    startup_deadline = time.time() + 2.0
    while True:
        # Wait for a new frame or a heartbeat timeout
        with cond:
            cond.wait_for(lambda: (frame_id != last_seen) or (latest_jpeg is not None and time.time() > startup_deadline),
                          timeout=1.0)
            jpg = latest_jpeg
            last_seen = frame_id

        if jpg is None:
            # No frame yet; keep connection alive with another loop
            continue

        # Standard MJPEG chunk
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n"
               b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" +
               jpg + b"\r\n")

@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/video")
def video():
    return Response(mjpeg_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    # Start the single capture/encode thread
    t = threading.Thread(target=camera_loop, kwargs={
        "cam_index": 0,          # change to 1/2 if you have multiple cameras
        "target_fps": 20,        # adjust for bandwidth/CPU
        # "width": 1280, "height": 720,  # optionally request a resolution your camera supports
        "jpeg_quality": 80,      # 60–85 is a good range
    }, daemon=True)
    t.start()
    try:
        # Visit http://127.0.0.1:5000 from multiple browsers/devices (same LAN)
        app.run(host="0.0.0.0", port=8000, debug=False, threaded=True, use_reloader=False)
    finally:
        running = False
        with cond:
            cond.notify_all()
