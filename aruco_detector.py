import cv2
import numpy as np


class ChargerPose:
    

    def __init__(self, distance, bearing, payload, x=0.0, y=0.0, z=0.0):
        self.distance = distance  
        self.bearing = bearing    
        self.payload = payload    
        self.x = x                
        self.y = y                
        self.z = z                


class ArucoDetector:
    def __init__(self, marker_size_m=0.15, target_id=0,
                 dictionary="DICT_5X5_50", hfov_deg=70.0):
        
        self.marker_size_m = marker_size_m
        self.target_id = target_id
        self.hfov_deg = hfov_deg

        if not hasattr(cv2, "aruco") or not hasattr(cv2.aruco, "ArucoDetector"):
            raise RuntimeError(
            )
        if not hasattr(cv2.aruco, dictionary):
            raise ValueError(f"Неизвестный словарь ArUco: {dictionary}")

        self.aruco_dict = cv2.aruco.getPredefinedDictionary(
            getattr(cv2.aruco, dictionary)
        )
        self.aruco_params = cv2.aruco.DetectorParameters()
       
        self.aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        half = marker_size_m / 2.0
       
        self._object_points = np.array(
            [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
            dtype=np.float64,
        )

        self.has_camera = False
        self.camera_matrix = None
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float64)
        self._camera_from_fov = False
        self._fov_frame_size = None

       
        self._last_corners = ()
        self._last_ids = None

    
    def set_camera(self, camera_matrix, dist_coeffs=None):
        
        self.camera_matrix = np.asarray(camera_matrix, dtype=np.float64).reshape(3, 3)
        if dist_coeffs is None:
            self.dist_coeffs = np.zeros((5, 1), dtype=np.float64)
        else:
            self.dist_coeffs = np.asarray(dist_coeffs, dtype=np.float64).reshape(-1, 1)
        self.has_camera = True
        self._camera_from_fov = False

    def set_camera_from_fov(self, width, height, hfov_deg=70.0):
        
        fx = (width / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
        self.camera_matrix = np.array(
            [[fx, 0, width / 2.0], [0, fx, height / 2.0], [0, 0, 1]],
            dtype=np.float64,
        )
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float64)
        self.has_camera = True
        self._camera_from_fov = True
        self._fov_frame_size = (width, height)

    
    def detect(self, frame):
        
        h, w = frame.shape[:2]
        if not self.has_camera or (
            self._camera_from_fov and self._fov_frame_size != (w, h)
        ):
           
            self.set_camera_from_fov(w, h, self.hfov_deg)

        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        self._last_corners, self._last_ids = corners, ids

        if ids is None or len(ids) == 0:
            return None

        
        ids = np.asarray(ids).flatten()
        matches = np.where(ids == self.target_id)[0]
        if matches.size == 0:
            return None

        image_points = np.asarray(corners[matches[0]], dtype=np.float64).reshape(4, 2)

        tvec = self._solve(image_points)
        if tvec is None:
            return None

        x, y, z = (float(v) for v in tvec.ravel())
        if z <= 0: 
            return None

        return ChargerPose(
            distance=float(np.hypot(x, z)),
            bearing=float(np.arctan2(x, z)),
            payload=str(self.target_id),
            x=x, y=y, z=z,
        )

    def _solve(self, image_points):
       
        for flag in (cv2.SOLVEPNP_IPPE_SQUARE, cv2.SOLVEPNP_ITERATIVE):
            ok, _, tvec = cv2.solvePnP(
                self._object_points, image_points,
                self.camera_matrix, self.dist_coeffs, flags=flag,
            )
            if ok and np.all(np.isfinite(tvec)):
                return tvec
        return None

    def draw_debug(self, frame, pose):
       
        if self._last_ids is not None and len(self._last_ids) > 0:
            ids = np.asarray(self._last_ids).reshape(-1, 1).astype(np.int32)
            cv2.aruco.drawDetectedMarkers(frame, self._last_corners, ids)

        if pose:
            text = (f"dist={pose.distance:.2f}m "
                    f"angle={np.degrees(pose.bearing):+.1f}deg")
            cv2.putText(frame, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, f"Marker id={self.target_id} not found", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame