# -*- coding: utf-8 -*-
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
import math
import time

app = FastAPI(title="ArUco Docking API")

api_data = {
    "status": "starting",
    "marker": None,
    "robot_command": None,
    "frame_bytes": None
}

@app.get("/health")
def health():
    return {"ok": True, "status": api_data["status"], "last_error": None}

@app.get("/api/v1/detections")
def get_detections():
    return {
        "status": api_data["status"],
        "marker": api_data["marker"],
        "robot_command": api_data["robot_command"]
    }

def update_state(pose, state_name, v, w):
    api_data["status"] = "running"
    if pose is None:
        api_data["marker"] = None
        api_data["robot_command"] = None
    else:
        bearing_deg = math.degrees(pose.bearing)
        direction = "RIGHT" if bearing_deg > 0 else "LEFT"
        api_data["marker"] = {
            "id": str(pose.payload),
            "distance_m": round(pose.distance, 2),
            "bearing_deg": round(bearing_deg, 1),
            "direction": direction,
            "x_m": round(pose.x, 2),
            "z_m": round(pose.z, 2)
        }
        api_data["robot_command"] = {
            "linear_x": round(v, 2),
            "angular_z": round(w, 2)
        }

def generate_frames():
    while True:
        if api_data["frame_bytes"] is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + api_data["frame_bytes"] + b'\r\n')
        time.sleep(0.05)

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/visualizer", response_class=HTMLResponse)
def visualizer():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>3D ArUco Visualizer</title>
        <style>
            body { margin: 0; overflow: hidden; background-color: #111; color: white; font-family: sans-serif; }
            #info { position: absolute; top: 10px; left: 10px; z-index: 100; background: rgba(0,0,0,0.7); padding: 15px; border-radius: 8px; border: 1px solid #333; }
            h3 { margin-top: 0; color: #00aaff; }
        </style>
    </head>
    <body>
        <div id="info">
            <h3>3D Visualization</h3>
            <p>Distance: <span id="dist" style="font-weight: bold; color: #00ff00;">0.00</span> m</p>
            <p>Angle: <span id="angle" style="font-weight: bold; color: #00ff00;">0.0</span> deg</p>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script>
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

            const light = new THREE.DirectionalLight(0xffffff, 1);
            light.position.set(1, 1, 1).normalize();
            scene.add(light);
            
            const ambientLight = new THREE.AmbientLight(0x404040);
            scene.add(ambientLight);

            const grid = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
            grid.position.y = -0.1;
            scene.add(grid);

            const robotGeo = new THREE.ConeGeometry(0.15, 0.4, 8);
            const robotMat = new THREE.MeshLambertMaterial({color: 0x00aaff});
            const robot = new THREE.Mesh(robotGeo, robotMat);
            robot.rotation.x = Math.PI / 2;
            scene.add(robot);

            const markerGeo = new THREE.BoxGeometry(0.2, 0.2, 0.2);
            const markerMat = new THREE.MeshLambertMaterial({color: 0x00ff00});
            const marker = new THREE.Mesh(markerGeo, markerMat);
            scene.add(marker);

            const lineGeometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,-1)]);
            const lineMaterial = new THREE.LineBasicMaterial({color: 0xffffff});
            const line = new THREE.Line(lineGeometry, lineMaterial);
            scene.add(line);

            camera.position.set(0, 4, 4);
            camera.lookAt(0, 0, 0);

            async function updateData() {
                try {
                    const response = await fetch('/api/v1/detections');
                    const data = await response.json();
                    
                    if (data.marker) {
                        const dist = data.marker.distance_m;
                        const bearing = data.marker.bearing_deg;
                        
                        document.getElementById('dist').textContent = dist.toFixed(2);
                        document.getElementById('angle').textContent = bearing.toFixed(1);

                        const rad = bearing * Math.PI / 180;
                        const x = dist * Math.sin(rad);
                        const z = -dist * Math.cos(rad);
                        
                        marker.position.set(x, 0, z);
                        
                        const points = [new THREE.Vector3(0,0,0), marker.position.clone()];
                        line.geometry.setFromPoints(points);
                    } else {
                        document.getElementById('dist').textContent = "---";
                        document.getElementById('angle').textContent = "---";
                        marker.position.set(0, -10, 0);
                    }
                } catch (e) {
                    console.error(e);
                }
                requestAnimationFrame(updateData);
            }

            updateData();

            function animate() {
                requestAnimationFrame(animate);
                renderer.render(scene, camera);
            }
            animate();
        </script>
    </body>
    </html>
    """
    return html_content

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")