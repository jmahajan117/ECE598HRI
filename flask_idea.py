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
          body { 
            margin: 0; 
            background: #111; 
            display: flex; 
            flex-direction: column;
            align-items: center; 
            justify-content: center; 
            height: 100vh; 
            color: white;
            font-family: Arial, sans-serif;
          }
          #container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
          }
          #video-container {
            position: relative;
            display: inline-block;
          }
          #video-feed {
            max-width: 95vw; 
            max-height: 80vh; 
            box-shadow: 0 10px 40px rgba(0,0,0,.6); 
            border-radius: 12px;
            cursor: crosshair;
          }
          #overlay-canvas {
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;
            border-radius: 12px;
          }
          #coords-display {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            min-width: 300px;
            text-align: center;
          }
          .coord-line {
            margin: 8px 0;
          }
          .coord-label {
            color: #888;
            margin-right: 10px;
          }
          .coord-value {
            color: #4CAF50;
            font-weight: bold;
          }
          .point1 { color: #FF5722; }
          .point2 { color: #2196F3; }
          #send-button {
            display: none;
            padding: 12px 40px;
            font-size: 18px;
            font-weight: bold;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
            transition: all 0.3s ease;
          }
          #send-button:hover {
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(76, 175, 80, 0.6);
          }
          #send-button:active {
            transform: translateY(0);
          }
          #send-button.show {
            display: block;
          }
        </style>
      </head>
      <body>
        <div id="container">
          <div id="video-container">
            <img id="video-feed" src="/video" alt="camera stream" />
            <canvas id="overlay-canvas"></canvas>
          </div>
          <div id="coords-display">
            <div class="coord-line">
              <span class="coord-label point1">Point 1:</span>
              <span class="coord-value" id="point1-coords">Click on the video</span>
            </div>
            <div class="coord-line">
              <span class="coord-label point2">Point 2:</span>
              <span class="coord-value" id="point2-coords">Click again for second point</span>
            </div>
          </div>
          <button id="send-button">Send</button>
        </div>

        <script>
          const videoFeed = document.getElementById('video-feed');
          const canvas = document.getElementById('overlay-canvas');
          const ctx = canvas.getContext('2d');
          const point1Display = document.getElementById('point1-coords');
          const point2Display = document.getElementById('point2-coords');
          const sendButton = document.getElementById('send-button');

          let point1 = null;
          let point2 = null;
          let clickCount = 0;

          // Update canvas size to match image
          function updateCanvasSize() {
            canvas.width = videoFeed.offsetWidth;
            canvas.height = videoFeed.offsetHeight;
            drawPoints();
          }

          videoFeed.onload = updateCanvasSize;
          window.addEventListener('resize', updateCanvasSize);

          function drawPoints() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (point1) {
              ctx.beginPath();
              ctx.arc(point1.displayX, point1.displayY, 8, 0, 2 * Math.PI);
              ctx.fillStyle = '#FF5722';
              ctx.fill();
              ctx.strokeStyle = 'white';
              ctx.lineWidth = 2;
              ctx.stroke();
              
              ctx.font = 'bold 16px Arial';
              ctx.fillStyle = 'white';
              ctx.fillText('1', point1.displayX - 5, point1.displayY - 12);
            }
            
            if (point2) {
              ctx.beginPath();
              ctx.arc(point2.displayX, point2.displayY, 8, 0, 2 * Math.PI);
              ctx.fillStyle = '#2196F3';
              ctx.fill();
              ctx.strokeStyle = 'white';
              ctx.lineWidth = 2;
              ctx.stroke();
              
              ctx.font = 'bold 16px Arial';
              ctx.fillStyle = 'white';
              ctx.fillText('2', point2.displayX - 5, point2.displayY - 12);
            }
          }

          videoFeed.addEventListener('click', function(e) {
            const rect = videoFeed.getBoundingClientRect();
            const displayX = e.clientX - rect.left;
            const displayY = e.clientY - rect.top;
            
            // Calculate actual image coordinates
            const scaleX = videoFeed.naturalWidth / videoFeed.offsetWidth;
            const scaleY = videoFeed.naturalHeight / videoFeed.offsetHeight;
            const actualX = Math.round(displayX * scaleX);
            const actualY = Math.round(displayY * scaleY);

            clickCount++;
            
            if (clickCount === 1) {
              point1 = { displayX, displayY, actualX, actualY };
              point1Display.textContent = `(${actualX}, ${actualY})`;
              point2 = null;
              point2Display.textContent = 'Click again for second point';
              sendButton.classList.remove('show');
            } else if (clickCount === 2) {
              point2 = { displayX, displayY, actualX, actualY };
              point2Display.textContent = `(${actualX}, ${actualY})`;
              sendButton.classList.add('show');
              clickCount = 0;  // Reset for next pair of clicks
            }
            
            drawPoints();
          });

          sendButton.addEventListener('click', function() {
            sendCoordinates();
            sendButton.classList.remove('show');
            
            // Clear the points and reset the interface
            point1 = null;
            point2 = null;
            clickCount = 0;
            point1Display.textContent = 'Click on the video';
            point2Display.textContent = 'Click again for second point';
            ctx.clearRect(0, 0, canvas.width, canvas.height);
          });

          function sendCoordinates() {
            if (point1 && point2) {
              const formData = new FormData();
              formData.append('x1', point1.actualX);
              formData.append('y1', point1.actualY);
              formData.append('x2', point2.actualX);
              formData.append('y2', point2.actualY);
              formData.append('action', '1');
              
              fetch('/send_coords', {
                method: 'POST',
                body: formData
              })
              .then(response => response.text())
              .then(data => console.log('Coordinates sent:', data))
              .catch(error => console.error('Error:', error));
            }
          }
        </script>
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
    app.run(host="0.0.0.0", port=72, debug=False, threaded=True, use_reloader=False)
