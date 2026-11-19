# -*- coding: utf-8 -*-
import time
import threading
import cv2

import config
from aruco_detector import ArucoDetector
from docking_logic import DockingLogic, State
import api_server

def main():
    # --- Запуск API-сервера в фоновом потоке ---
    api_thread = threading.Thread(target=api_server.run_server, daemon=True)
    api_thread.start()
    print("=> API: http://127.0.0.1:8000/docs")
    print("=> Video: http://127.0.0.1:8000/video_feed")
    # ------------------------------------------

    # Открываем видеофайл
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"Ошибка: не удалось открыть файл {config.CAMERA_INDEX}.")
        return 1

    detector = ArucoDetector(
        marker_size_m=config.MARKER_SIZE_M,
        hfov_deg=config.HFOV_DEG,
    )

    # Тестовая заглушка для моторов (чтобы не было ошибки без ROS)
    class FakeMotors:
        def drive(self, v, w): pass
        def stop(self): pass
        def cleanup(self): pass

    motors = FakeMotors()
    logic = DockingLogic(**config.DOCKING_PARAMS)

    print(f"Запущен тест на видео. Ищу ArUco-доску...")

    last_state = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                # Если видео закончилось, начинаем сначала
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            now = time.time()
            pose = detector.detect(frame)
            state, v, w = logic.step(pose, now)
            
            # Обновляем данные для API
            api_server.update_state(pose, state.value, v, w)
            
            # Рисуем отладку и отправляем в видео-стрим
            debug_frame = detector.draw_debug(frame.copy(), pose)
            cv2.putText(debug_frame, f"State: {state.value}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            _, buffer = cv2.imencode('.jpg', debug_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            api_server.api_data["frame_bytes"] = buffer.tobytes()

            if state != last_state:
                print(f"Состояние: {state.value}")
                last_state = state

            # Небольшая задержка, чтобы видео не летело слишком быстро
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("Остановка...")
    finally:
        cap.release()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())