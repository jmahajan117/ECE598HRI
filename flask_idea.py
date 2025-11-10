# app.py
import cv2
from flask import Flask, Response, render_template_string, request
import json


class CameraStreamApp:
    HTML = """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Camera Stream</title>
        <style>
          body { margin: 0; background: #111; display:flex; align-items:center; justify-content:center; height:100vh; }
          img { max-width: 95vw; max-height: 95vh; box-shadow: 0 10px 40px rgba(0,0,0,.6); border-radius: 12px; }
        </style>
      </head>
      <body>
        <img src="/video" alt="camera stream" />
      </body>
    </html>
    """

    def __init__(self, camera_index=0):
        self.app = Flask(__name__)
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None
        self.camera_index = camera_index
        self.curr_frame = None
        self.action = 1
        self._register_routes()

    def _register_routes(self):
        """Register all Flask routes"""
        self.app.get("/")(self.index)
        self.app.post("/send_coords")(self.send_coords)
        self.app.route("/get_data")(self.get_data)
        self.app.get("/video")(self.video)

    def frames(self):
        """Generator function for video frames"""
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise RuntimeError("Could not open camera")

        # Optional: set resolution (comment out if not supported)
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                # (Optional) flip for selfie view:
                # frame = cv2.flip(frame, 1)

                # Encode as JPEG
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if self.curr_frame is None:
                    self.curr_frame = frame
                    print(self.curr_frame.shape)
                if not ok:
                    continue
                jpg = buf.tobytes()

                # multipart/x-mixed-replace chunk
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" +
                       jpg + b"\r\n")
        finally:
            cap.release()

    def index(self):
        """Route handler for index page"""
        return render_template_string(self.HTML)

    def send_coords(self):
        """Route handler for receiving coordinates"""
        data = request.form.get("x1")
        data2 = request.form.get("y1")
        data3 = request.form.get("x2")
        data4 = request.form.get("y2")
        data5 = request.form.get("action")
        self.x1 = data
        self.y1 = data2
        self.x2 = data3
        self.y2 = data4
        self.action = data5
        return "recieved"

    
    def get_data(self):
        """Route handler for getting coordinates"""
        if self.x1 is None or self.y1 is None or self.x2 is None or self.y2 is None:
            return Response(status=400)
        frame = self.curr_frame.tolist()
        all_data = {"action": self.action, "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "frame": frame}
        response = self.app.response_class(
            response=json.dumps(all_data),
            status=200,
            mimetype='application/json'
        )
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None
        self.curr_frame = None
        return response

    def video(self):
        """Route handler for video stream"""
        return Response(self.frames(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    def run(self, host="0.0.0.0", port=8000, debug=False, threaded=True, use_reloader=False):
        """Run the Flask application"""
        self.app.run(host=host, port=port, debug=debug, threaded=threaded, use_reloader=use_reloader)


if __name__ == "__main__":
    # For local testing: http://127.0.0.1:8000
    # Expose on your LAN: host="0.0.0.0" (then visit http://<your-ip>:8000)
    app = CameraStreamApp(camera_index=0)
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True, use_reloader=False)
