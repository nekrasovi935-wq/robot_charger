import argparse
import sys
import io
import time
import threading

import cv2

import config
from aruco_detector import ArucoDetector
from docking_logic import DockingLogic, State
from motor_controller import MotorController
import api_server


if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_args():
    p = argparse.ArgumentParser(description="Подъезд к зарядке по ArUco-маркеру")
    p.add_argument("--no-window", action="store_true",
                   help="не показывать окно с видео (для SSH)")
    p.add_argument("--dry-run", action="store_true",
                   help="не отправлять команды в ROS, только печатать")
    p.add_argument("--camera", type=int, default=config.CAMERA_INDEX,
                   help="номер камеры (по умолчанию из config.py)")
    p.add_argument("--marker-size", type=float, default=config.MARKER_SIZE_M,
                   help="сторона чёрного квадрата маркера, м")
    p.add_argument("--target-id", type=int, default=config.TARGET_ID,
                   help="ID маркера на зарядке")
    return p.parse_args()


def main():
    args = parse_args()

    
    api_thread = threading.Thread(target=api_server.run_server, daemon=True)
    api_thread.start()
    print("=> API-сервер запущен на http://127.0.0.1:8000/docs")
    
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print(f"Ошибка: не удалось открыть камеру {args.camera}.")
        return 1

    detector = ArucoDetector(
        marker_size_m=args.marker_size,
        target_id=args.target_id,
        dictionary=config.ARUCO_DICTIONARY,
        hfov_deg=config.HFOV_DEG,
    )
    if config.CAMERA_MATRIX is not None:
        detector.set_camera(config.CAMERA_MATRIX, config.DIST_COEFFS)
    else:
        print(f"Камера не откалибрована: использую угол обзора {config.HFOV_DEG}° "
              "(расстояние будет приблизительным).")

    logic = DockingLogic(**config.DOCKING_PARAMS)
    motors = MotorController(topic=config.CMD_VEL_TOPIC,
                             use_ros=False if args.dry_run else None)

    print(f"Робот запущен. Ищу ArUco-маркер id={args.target_id} "
          f"({config.ARUCO_DICTIONARY}, {args.marker_size * 100:.1f} см)...")

    last_print = 0.0
    last_state = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
               
                motors.stop()
                print("Не удалось прочитать кадр с камеры, повтор...")
                time.sleep(0.1)
                continue

            now = time.time()
            pose = detector.detect(frame)
            state, v, w = logic.step(pose, now)
            
            
            api_server.update_state(pose, state.value, v, w)
            
            motors.drive(v, w)

            if state != last_state:
                print(f"Состояние: {state.value}")
                last_state = state
                
            if state == State.DOCKED:
                if now - last_print > 2.0:
                    print("Зарядная станция достигнута, робот остановлен.")
                    last_print = now
            elif args.no_window and now - last_print > 0.5:
               
                if pose:
                    print(f"  dist={pose.distance:.2f} м  "
                          f"угол={pose.bearing * 57.2958:+.1f}°  v={v:.2f}  w={w:+.2f}")
                else:
                    print("  маркер не виден")
                last_print = now

            if not args.no_window:
                debug_frame = detector.draw_debug(frame, pose)
                cv2.putText(debug_frame, f"State: {state.value}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.imshow("Robot", debug_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("Остановка...")
    finally:
        motors.cleanup()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())